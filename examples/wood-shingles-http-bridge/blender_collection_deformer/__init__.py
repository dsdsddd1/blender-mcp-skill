bl_info = {
    "name": "Collection Geometry Deformer Bridge",
    "author": "OpenAI Codex",
    "version": (0, 3, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > Collection Deform",
    "description": "Expose an HTTP bridge that builds a collection-based Geometry Nodes deformer",
    "category": "Object",
}

import importlib.util
import json
import math
import os
import socket
import traceback
from urllib.parse import urlsplit

import bpy
from bpy.props import PointerProperty
from bpy.types import Operator, Panel, PropertyGroup


NODE_GROUP_NAME = "CD_CollectionDeform"
MODIFIER_NAME = "CD_CollectionDeform"
GROUP_VERSION = 2
SHINGLE_NODE_GROUP_NAME = "CD_WoodShingles"
SHINGLE_MODIFIER_NAME = "CD_WoodShingles"
SHINGLE_GROUP_VERSION = 13
DEFAULT_DEV_OVERRIDE_PATH = os.path.join(os.path.dirname(__file__), "dev_override.py")
MAX_REQUEST_SIZE = 1024 * 1024
BRIDGE_TIMER_INTERVAL = 0.1
DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 8765

BRIDGE_STATE = {
    "server_socket": None,
    "host": DEFAULT_BRIDGE_HOST,
    "port": DEFAULT_BRIDGE_PORT,
    "clients": {},
    "timer_registered": False,
    "token": "",
    "stop_requested": False,
}

DEV_OVERRIDE_STATE = {
    "path": "",
    "mtime": None,
    "module": None,
    "error": "",
}


def _clear_node_group_interface(node_group):
    if not hasattr(node_group, "interface"):
        return
    items = list(node_group.interface.items_tree)
    for item in reversed(items):
        if item.item_type in {"SOCKET", "PANEL"}:
            node_group.interface.remove(item)


def _add_socket(
    node_group,
    name,
    in_out,
    socket_type,
    *,
    description="",
    default_value=None,
    min_value=None,
    max_value=None,
):
    if hasattr(node_group, "interface"):
        try:
            socket_item = node_group.interface.new_socket(
                name=name,
                in_out=in_out,
                socket_type=socket_type,
            )
        except (RuntimeError, TypeError):
            socket_item = None
    else:
        socket_item = None

    if socket_item is None:
        sockets = node_group.inputs if in_out == "INPUT" else node_group.outputs
        socket_item = sockets.new(socket_type, name)

    if description and hasattr(socket_item, "description"):
        socket_item.description = description
    if default_value is not None and hasattr(socket_item, "default_value"):
        socket_item.default_value = default_value
    if min_value is not None and hasattr(socket_item, "min_value"):
        socket_item.min_value = min_value
    if max_value is not None and hasattr(socket_item, "max_value"):
        socket_item.max_value = max_value
    return socket_item


def _find_interface_socket(node_group, name, in_out="INPUT"):
    if hasattr(node_group, "interface"):
        for item in node_group.interface.items_tree:
            if item.item_type == "SOCKET" and item.in_out == in_out and item.name == name:
                return item
        return None

    sockets = node_group.inputs if in_out == "INPUT" else node_group.outputs
    return sockets.get(name)


def _new_node(nodes, *candidates):
    for bl_idname in candidates:
        try:
            return nodes.new(bl_idname)
        except RuntimeError:
            continue
    raise RuntimeError(f"Unable to create node. Tried: {', '.join(candidates)}")


def _node_socket(node, kind, *names, index=None):
    sockets = node.inputs if kind == "INPUT" else node.outputs
    for name in names:
        if name in sockets:
            return sockets[name]
    if index is not None:
        return sockets[index]
    raise KeyError(
        f"Socket not found on {node.bl_idname}: {', '.join(names) if names else index}"
    )


def _build_node_group(node_group):
    node_group.nodes.clear()
    node_group.links.clear()
    _clear_node_group_interface(node_group)

    if hasattr(node_group, "is_modifier"):
        node_group.is_modifier = True

    _add_socket(
        node_group,
        "Collection",
        "INPUT",
        "NodeSocketCollection",
        description="Source collection to import into the node tree.",
    )
    _add_socket(
        node_group,
        "Strength",
        "INPUT",
        "NodeSocketFloat",
        description="Vertical deformation amount applied after realizing instances.",
        default_value=0.35,
        min_value=-10.0,
        max_value=10.0,
    )
    _add_socket(
        node_group,
        "Noise Scale",
        "INPUT",
        "NodeSocketFloat",
        description="Controls the size of the deformation noise pattern.",
        default_value=1.5,
        min_value=0.001,
        max_value=1000.0,
    )
    _add_socket(
        node_group,
        "Translation",
        "INPUT",
        "NodeSocketVector",
        description="Move the imported collection before deformation.",
        default_value=(0.0, 0.0, 0.0),
    )
    _add_socket(
        node_group,
        "Scale",
        "INPUT",
        "NodeSocketVector",
        description="Scale the imported collection before deformation.",
        default_value=(1.0, 1.0, 1.0),
    )
    _add_socket(
        node_group,
        "Geometry",
        "OUTPUT",
        "NodeSocketGeometry",
        description="Deformed geometry output.",
    )

    nodes = node_group.nodes
    links = node_group.links

    group_input = _new_node(nodes, "NodeGroupInput")
    group_input.location = (-900, 0)

    collection_info = _new_node(nodes, "GeometryNodeCollectionInfo")
    collection_info.location = (-650, 140)
    if hasattr(collection_info, "transform_space"):
        collection_info.transform_space = "RELATIVE"

    realize_instances = _new_node(nodes, "GeometryNodeRealizeInstances")
    realize_instances.location = (-380, 140)

    transform = _new_node(nodes, "GeometryNodeTransform")
    transform.location = (-120, 140)

    set_position = _new_node(nodes, "GeometryNodeSetPosition")
    set_position.location = (420, 140)

    position = _new_node(nodes, "GeometryNodeInputPosition")
    position.location = (-120, -220)

    noise = _new_node(nodes, "ShaderNodeTexNoise")
    noise.location = (120, -220)

    subtract = _new_node(nodes, "ShaderNodeMath")
    subtract.location = (420, -180)
    subtract.operation = "SUBTRACT"
    subtract.inputs[1].default_value = 0.5

    multiply = _new_node(nodes, "ShaderNodeMath")
    multiply.location = (660, -180)
    multiply.operation = "MULTIPLY"

    combine_xyz = _new_node(nodes, "ShaderNodeCombineXYZ")
    combine_xyz.location = (900, -180)

    group_output = _new_node(nodes, "NodeGroupOutput")
    group_output.location = (1160, 140)

    links.new(collection_info.inputs["Collection"], group_input.outputs["Collection"])
    links.new(realize_instances.inputs["Geometry"], collection_info.outputs[0])
    links.new(transform.inputs["Geometry"], realize_instances.outputs["Geometry"])
    links.new(transform.inputs["Translation"], group_input.outputs["Translation"])
    links.new(transform.inputs["Scale"], group_input.outputs["Scale"])
    links.new(set_position.inputs["Geometry"], transform.outputs["Geometry"])

    links.new(noise.inputs["Vector"], position.outputs["Position"])
    links.new(noise.inputs["Scale"], group_input.outputs["Noise Scale"])
    links.new(subtract.inputs[0], noise.outputs["Fac"])
    links.new(multiply.inputs[0], subtract.outputs["Value"])
    links.new(multiply.inputs[1], group_input.outputs["Strength"])
    links.new(combine_xyz.inputs["Z"], multiply.outputs["Value"])
    links.new(set_position.inputs["Offset"], combine_xyz.outputs["Vector"])

    links.new(group_output.inputs["Geometry"], set_position.outputs["Geometry"])

    node_group["cd_group_version"] = GROUP_VERSION


def ensure_node_group():
    node_group = bpy.data.node_groups.get(NODE_GROUP_NAME)
    if node_group is None or node_group.bl_idname != "GeometryNodeTree":
        node_group = bpy.data.node_groups.new(NODE_GROUP_NAME, "GeometryNodeTree")
        _build_node_group(node_group)
        return node_group

    if node_group.get("cd_group_version") != GROUP_VERSION:
        _build_node_group(node_group)

    return node_group


def _build_wood_shingles_node_group_default(node_group):
    node_group.nodes.clear()
    node_group.links.clear()
    _clear_node_group_interface(node_group)

    if hasattr(node_group, "is_modifier"):
        node_group.is_modifier = True

    _add_socket(
        node_group,
        "Geometry",
        "INPUT",
        "NodeSocketGeometry",
        description="Surface geometry that will receive wooden shingles.",
    )
    _add_socket(
        node_group,
        "Columns",
        "INPUT",
        "NodeSocketInt",
        description="Number of shingles across X.",
        default_value=8,
        min_value=1,
        max_value=10000,
    )
    _add_socket(
        node_group,
        "Rows",
        "INPUT",
        "NodeSocketInt",
        description="Number of shingles across Y.",
        default_value=8,
        min_value=1,
        max_value=10000,
    )
    _add_socket(
        node_group,
        "Tile Size",
        "INPUT",
        "NodeSocketFloat",
        description="Base width and length of each square shingle.",
        default_value=0.18,
        min_value=0.001,
        max_value=100.0,
    )
    _add_socket(
        node_group,
        "Thickness",
        "INPUT",
        "NodeSocketFloat",
        description="Base thickness of each shingle.",
        default_value=0.025,
        min_value=0.001,
        max_value=10.0,
    )
    _add_socket(
        node_group,
        "Scale Jitter",
        "INPUT",
        "NodeSocketFloat",
        description="How much the square footprint varies per shingle.",
        default_value=0.12,
        min_value=0.0,
        max_value=1.0,
    )
    _add_socket(
        node_group,
        "Thickness Jitter",
        "INPUT",
        "NodeSocketFloat",
        description="How much the thickness varies per shingle.",
        default_value=0.35,
        min_value=0.0,
        max_value=1.0,
    )
    _add_socket(
        node_group,
        "Rotation Jitter",
        "INPUT",
        "NodeSocketFloat",
        description="Maximum random twist around the local normal, in radians.",
        default_value=math.radians(10.0),
        min_value=0.0,
        max_value=math.pi,
    )
    _add_socket(
        node_group,
        "Surface Offset",
        "INPUT",
        "NodeSocketFloat",
        description="Offset shingles slightly above the surface.",
        default_value=0.012,
        min_value=0.0,
        max_value=10.0,
    )
    _add_socket(
        node_group,
        "Top Face Threshold",
        "INPUT",
        "NodeSocketFloat",
        description="Only faces with upward normals above this threshold receive shingles.",
        default_value=0.0,
        min_value=-1.0,
        max_value=1.0,
    )
    _add_socket(
        node_group,
        "Row Overlap",
        "INPUT",
        "NodeSocketFloat",
        description="Extra shingle length along the row direction for a subtle overlap.",
        default_value=0.18,
        min_value=0.0,
        max_value=1.0,
    )
    _add_socket(
        node_group,
        "Seed",
        "INPUT",
        "NodeSocketInt",
        description="Random seed for shingle variation.",
        default_value=0,
        min_value=-2147483648,
        max_value=2147483647,
    )
    _add_socket(
        node_group,
        "Geometry",
        "OUTPUT",
        "NodeSocketGeometry",
        description="Surface with procedural wooden shingles.",
    )

    nodes = node_group.nodes
    links = node_group.links

    group_input = _new_node(nodes, "NodeGroupInput")
    group_input.location = (-2400, 0)

    input_normal = _new_node(nodes, "GeometryNodeInputNormal")
    input_normal.location = (-2180, -220)

    separate_normal = _new_node(nodes, "ShaderNodeSeparateXYZ")
    separate_normal.location = (-1960, -220)

    compare_up = _new_node(nodes, "FunctionNodeCompare")
    compare_up.location = (-1740, -220)
    compare_up.data_type = "FLOAT"
    compare_up.operation = "GREATER_THAN"

    separate_geometry = _new_node(nodes, "GeometryNodeSeparateGeometry")
    separate_geometry.location = (-1520, 0)
    try:
        separate_geometry.domain = "FACE"
    except Exception:
        pass

    bool_true = _new_node(nodes, "FunctionNodeInputBool")
    bool_true.location = (-1740, 220)
    bool_true.boolean = True

    bool_false = _new_node(nodes, "FunctionNodeInputBool")
    bool_false.location = (-1740, 340)
    bool_false.boolean = False

    uv_unwrap = _new_node(nodes, "GeometryNodeUVUnwrap")
    uv_unwrap.location = (-1280, 0)
    if hasattr(uv_unwrap, "method"):
        uv_unwrap.method = "ANGLE_BASED"

    columns_plus_one = _new_node(nodes, "FunctionNodeIntegerMath")
    columns_plus_one.location = (-1280, -360)
    columns_plus_one.operation = "ADD"
    columns_plus_one.inputs[1].default_value = 1

    rows_plus_one = _new_node(nodes, "FunctionNodeIntegerMath")
    rows_plus_one.location = (-1280, -460)
    rows_plus_one.operation = "ADD"
    rows_plus_one.inputs[1].default_value = 1

    mesh_grid = _new_node(nodes, "GeometryNodeMeshGrid")
    mesh_grid.location = (-1040, -360)

    uv_grid_translate = _new_node(nodes, "ShaderNodeCombineXYZ")
    uv_grid_translate.location = (-1280, -620)
    uv_grid_translate.inputs["X"].default_value = 0.5
    uv_grid_translate.inputs["Y"].default_value = 0.5

    transform_grid = _new_node(nodes, "GeometryNodeTransform")
    transform_grid.location = (-800, -360)

    mesh_to_points = _new_node(nodes, "GeometryNodeMeshToPoints")
    mesh_to_points.location = (-560, -360)
    try:
        mesh_to_points.mode = "FACES"
    except Exception:
        pass

    sample_position = _new_node(nodes, "GeometryNodeSampleUVSurface")
    sample_position.location = (-560, -40)
    sample_position.data_type = "FLOAT_VECTOR"

    sample_normal = _new_node(nodes, "GeometryNodeSampleUVSurface")
    sample_normal.location = (-560, 180)
    sample_normal.data_type = "FLOAT_VECTOR"

    valid_points = _new_node(nodes, "GeometryNodeSeparateGeometry")
    valid_points.location = (-320, -360)
    try:
        valid_points.domain = "POINT"
    except Exception:
        pass

    set_position = _new_node(nodes, "GeometryNodeSetPosition")
    set_position.location = (-80, -360)

    rotation_input = _new_node(nodes, "FunctionNodeInputRotation")
    rotation_input.location = (-320, 420)

    align_to_normal = _new_node(nodes, "FunctionNodeAlignEulerToVector")
    align_to_normal.location = (-80, 200)
    align_to_normal.axis = "Z"
    align_to_normal.pivot_axis = "AUTO"

    cube = _new_node(nodes, "GeometryNodeMeshCube")
    cube.location = (-320, 700)

    scale_xy = _new_node(nodes, "ShaderNodeMath")
    scale_xy.location = (-560, 700)
    scale_xy.operation = "MULTIPLY"

    thickness_half = _new_node(nodes, "ShaderNodeMath")
    thickness_half.location = (-560, 620)
    thickness_half.operation = "MULTIPLY"
    thickness_half.inputs[1].default_value = 0.5

    translate_z = _new_node(nodes, "ShaderNodeMath")
    translate_z.location = (-320, 820)
    translate_z.operation = "ADD"

    combine_base_scale = _new_node(nodes, "ShaderNodeCombineXYZ")
    combine_base_scale.location = (-320, 620)

    combine_cube_translation = _new_node(nodes, "ShaderNodeCombineXYZ")
    combine_cube_translation.location = (-80, 820)

    transform_cube = _new_node(nodes, "GeometryNodeTransform")
    transform_cube.location = (160, 700)

    point_index = _new_node(nodes, "GeometryNodeInputIndex")
    point_index.location = (160, -740)

    random_id_xy = _new_node(nodes, "FunctionNodeIntegerMath")
    random_id_xy.location = (380, -700)
    random_id_xy.operation = "ADD"

    random_id_z = _new_node(nodes, "FunctionNodeIntegerMath")
    random_id_z.location = (380, -820)
    random_id_z.operation = "ADD"
    random_id_z.inputs[1].default_value = 1000

    random_id_rot = _new_node(nodes, "FunctionNodeIntegerMath")
    random_id_rot.location = (380, -940)
    random_id_rot.operation = "ADD"
    random_id_rot.inputs[1].default_value = 2000

    random_xy = _new_node(nodes, "FunctionNodeRandomValue")
    random_xy.location = (620, -700)
    random_xy.data_type = "FLOAT"

    random_z = _new_node(nodes, "FunctionNodeRandomValue")
    random_z.location = (620, -820)
    random_z.data_type = "FLOAT"

    random_rot = _new_node(nodes, "FunctionNodeRandomValue")
    random_rot.location = (620, -940)
    random_rot.data_type = "FLOAT"

    subtract_xy = _new_node(nodes, "ShaderNodeMath")
    subtract_xy.location = (860, -700)
    subtract_xy.operation = "SUBTRACT"
    subtract_xy.inputs[0].default_value = 1.0

    add_xy = _new_node(nodes, "ShaderNodeMath")
    add_xy.location = (1080, -700)
    add_xy.operation = "ADD"

    subtract_z = _new_node(nodes, "ShaderNodeMath")
    subtract_z.location = (860, -820)
    subtract_z.operation = "SUBTRACT"
    subtract_z.inputs[0].default_value = 1.0

    add_z = _new_node(nodes, "ShaderNodeMath")
    add_z.location = (1080, -820)
    add_z.operation = "ADD"

    negate_rotation = _new_node(nodes, "ShaderNodeMath")
    negate_rotation.location = (860, -940)
    negate_rotation.operation = "MULTIPLY"
    negate_rotation.inputs[1].default_value = -1.0

    combine_instance_scale = _new_node(nodes, "ShaderNodeCombineXYZ")
    combine_instance_scale.location = (1300, -760)

    combine_twist = _new_node(nodes, "ShaderNodeCombineXYZ")
    combine_twist.location = (1300, -940)

    instance_on_points = _new_node(nodes, "GeometryNodeInstanceOnPoints")
    instance_on_points.location = (420, -220)

    scale_instances = _new_node(nodes, "GeometryNodeScaleInstances")
    scale_instances.location = (660, -220)

    rotate_instances = _new_node(nodes, "GeometryNodeRotateInstances")
    rotate_instances.location = (900, -220)
    if hasattr(rotate_instances, "local_space"):
        rotate_instances.local_space = True

    realize_instances = _new_node(nodes, "GeometryNodeRealizeInstances")
    realize_instances.location = (1140, -220)

    join_geometry = _new_node(nodes, "GeometryNodeJoinGeometry")
    join_geometry.location = (1380, -220)

    group_output = _new_node(nodes, "NodeGroupOutput")
    group_output.location = (1620, -220)

    roof_geometry = _node_socket(separate_geometry, "OUTPUT", "Selection", index=0)
    roof_uv = _node_socket(uv_unwrap, "OUTPUT", "UV", index=0)
    grid_points = _node_socket(mesh_to_points, "OUTPUT", "Points", "Geometry", index=0)
    valid_geometry = _node_socket(valid_points, "OUTPUT", "Selection", index=0)
    sampled_position = _node_socket(sample_position, "OUTPUT", "Value", index=0)
    sampled_normal = _node_socket(sample_normal, "OUTPUT", "Value", index=0)

    row_index = _new_node(nodes, "FunctionNodeIntegerMath")
    row_index.location = (-560, -660)
    row_index.operation = "DIVIDE"

    row_parity = _new_node(nodes, "FunctionNodeIntegerMath")
    row_parity.location = (-320, -660)
    row_parity.operation = "MODULO"
    row_parity.inputs[1].default_value = 2

    uv_half_step = _new_node(nodes, "ShaderNodeMath")
    uv_half_step.location = (-560, -560)
    uv_half_step.operation = "DIVIDE"
    uv_half_step.inputs[0].default_value = 0.5

    stagger_amount = _new_node(nodes, "ShaderNodeMath")
    stagger_amount.location = (-80, -660)
    stagger_amount.operation = "MULTIPLY"

    stagger_vector = _new_node(nodes, "ShaderNodeCombineXYZ")
    stagger_vector.location = (160, -660)

    sample_uv = _new_node(nodes, "ShaderNodeVectorMath")
    sample_uv.location = (400, -660)
    sample_uv.operation = "ADD"

    row_overlap_scale = _new_node(nodes, "ShaderNodeMath")
    row_overlap_scale.location = (1080, -600)
    row_overlap_scale.operation = "ADD"
    row_overlap_scale.inputs[0].default_value = 1.0

    overlap_y_scale = _new_node(nodes, "ShaderNodeMath")
    overlap_y_scale.location = (1300, -600)
    overlap_y_scale.operation = "MULTIPLY"

    links.new(
        _node_socket(separate_normal, "INPUT", "Vector", index=0),
        _node_socket(input_normal, "OUTPUT", "Normal", index=0),
    )
    links.new(
        _node_socket(compare_up, "INPUT", "A", index=2),
        _node_socket(separate_normal, "OUTPUT", "Z"),
    )
    links.new(
        _node_socket(compare_up, "INPUT", "B", index=3),
        _node_socket(group_input, "OUTPUT", "Top Face Threshold"),
    )
    links.new(
        _node_socket(separate_geometry, "INPUT", "Geometry", index=0),
        _node_socket(group_input, "OUTPUT", "Geometry", index=0),
    )
    links.new(
        _node_socket(separate_geometry, "INPUT", "Selection", index=1),
        _node_socket(compare_up, "OUTPUT", "Result", index=0),
    )
    links.new(
        _node_socket(uv_unwrap, "INPUT", "Selection", index=1),
        _node_socket(bool_true, "OUTPUT", "Boolean", index=0),
    )
    links.new(
        _node_socket(uv_unwrap, "INPUT", "Seam", index=2),
        _node_socket(bool_false, "OUTPUT", "Boolean", index=0),
    )
    try:
        _node_socket(uv_unwrap, "INPUT", "Margin", index=3).default_value = 0.001
    except Exception:
        pass
    try:
        _node_socket(uv_unwrap, "INPUT", "Fill Holes", index=4).default_value = False
    except Exception:
        pass

    links.new(
        _node_socket(columns_plus_one, "INPUT", "Value", index=0),
        _node_socket(group_input, "OUTPUT", "Columns"),
    )
    links.new(
        _node_socket(rows_plus_one, "INPUT", "Value", index=0),
        _node_socket(group_input, "OUTPUT", "Rows"),
    )
    try:
        _node_socket(mesh_grid, "INPUT", "Size X", index=0).default_value = 1.0
        _node_socket(mesh_grid, "INPUT", "Size Y", index=1).default_value = 1.0
    except Exception:
        pass
    links.new(
        _node_socket(mesh_grid, "INPUT", "Vertices X", index=2),
        _node_socket(columns_plus_one, "OUTPUT", "Value", index=0),
    )
    links.new(
        _node_socket(mesh_grid, "INPUT", "Vertices Y", index=3),
        _node_socket(rows_plus_one, "OUTPUT", "Value", index=0),
    )
    links.new(
        _node_socket(transform_grid, "INPUT", "Geometry", index=0),
        _node_socket(mesh_grid, "OUTPUT", "Mesh", "Geometry", index=0),
    )
    links.new(
        _node_socket(transform_grid, "INPUT", "Translation", index=1),
        _node_socket(uv_grid_translate, "OUTPUT", "Vector", index=0),
    )
    links.new(
        _node_socket(mesh_to_points, "INPUT", "Mesh", "Geometry", index=0),
        _node_socket(transform_grid, "OUTPUT", "Geometry", "Mesh", index=0),
    )
    try:
        _node_socket(mesh_to_points, "INPUT", "Radius", index=2).default_value = 0.001
    except Exception:
        pass

    position_field = _new_node(nodes, "GeometryNodeInputPosition")
    position_field.location = (-800, 420)

    sampled_position_is_valid = _node_socket(sample_position, "OUTPUT", "Is Valid", index=1)

    links.new(
        _node_socket(row_index, "INPUT", "Value", index=0),
        _node_socket(point_index, "OUTPUT", "Index", index=0),
    )
    links.new(
        _node_socket(row_index, "INPUT", "Value", index=1),
        _node_socket(group_input, "OUTPUT", "Columns"),
    )
    links.new(
        _node_socket(row_parity, "INPUT", "Value", index=0),
        _node_socket(row_index, "OUTPUT", "Value", index=0),
    )
    links.new(
        uv_half_step.inputs[1],
        _node_socket(group_input, "OUTPUT", "Columns"),
    )
    links.new(
        stagger_amount.inputs[0],
        _node_socket(row_parity, "OUTPUT", "Value", index=0),
    )
    links.new(
        stagger_amount.inputs[1],
        uv_half_step.outputs["Value"],
    )
    links.new(stagger_vector.inputs["X"], stagger_amount.outputs["Value"])
    links.new(
        sample_uv.inputs[0],
        _node_socket(position_field, "OUTPUT", "Position", index=0),
    )
    links.new(
        sample_uv.inputs[1],
        _node_socket(stagger_vector, "OUTPUT", "Vector", index=0),
    )

    links.new(
        _node_socket(sample_position, "INPUT", "Mesh", index=0),
        roof_geometry,
    )
    links.new(
        _node_socket(sample_position, "INPUT", "Value", index=1),
        _node_socket(position_field, "OUTPUT", "Position", index=0),
    )
    links.new(
        _node_socket(sample_position, "INPUT", "Source UV Map", "UV Map", index=2),
        roof_uv,
    )
    links.new(
        _node_socket(sample_position, "INPUT", "Sample UV", index=3),
        _node_socket(sample_uv, "OUTPUT", "Vector", index=0),
    )

    links.new(
        _node_socket(sample_normal, "INPUT", "Mesh", index=0),
        roof_geometry,
    )
    links.new(
        _node_socket(sample_normal, "INPUT", "Value", index=1),
        _node_socket(input_normal, "OUTPUT", "Normal", index=0),
    )
    links.new(
        _node_socket(sample_normal, "INPUT", "Source UV Map", "UV Map", index=2),
        roof_uv,
    )
    links.new(
        _node_socket(sample_normal, "INPUT", "Sample UV", index=3),
        _node_socket(sample_uv, "OUTPUT", "Vector", index=0),
    )

    links.new(
        _node_socket(valid_points, "INPUT", "Geometry", index=0),
        grid_points,
    )
    links.new(
        _node_socket(valid_points, "INPUT", "Selection", index=1),
        sampled_position_is_valid,
    )
    links.new(
        _node_socket(set_position, "INPUT", "Geometry", index=0),
        valid_geometry,
    )
    links.new(
        _node_socket(set_position, "INPUT", "Position", index=2),
        sampled_position,
    )

    links.new(
        _node_socket(align_to_normal, "INPUT", "Rotation", index=0),
        _node_socket(rotation_input, "OUTPUT", "Rotation", index=0),
    )
    try:
        _node_socket(align_to_normal, "INPUT", "Factor", index=2).default_value = 1.0
    except Exception:
        pass
    links.new(
        _node_socket(align_to_normal, "INPUT", "Vector", index=1),
        sampled_normal,
    )

    try:
        _node_socket(cube, "INPUT", "Size").default_value = 1.0
    except Exception:
        pass
    links.new(scale_xy.inputs[0], _node_socket(group_input, "OUTPUT", "Tile Size"))
    links.new(thickness_half.inputs[0], _node_socket(group_input, "OUTPUT", "Thickness"))
    links.new(translate_z.inputs[0], thickness_half.outputs["Value"])
    links.new(translate_z.inputs[1], _node_socket(group_input, "OUTPUT", "Surface Offset"))
    links.new(combine_base_scale.inputs["X"], _node_socket(group_input, "OUTPUT", "Tile Size"))
    links.new(combine_base_scale.inputs["Y"], _node_socket(group_input, "OUTPUT", "Tile Size"))
    links.new(combine_base_scale.inputs["Z"], _node_socket(group_input, "OUTPUT", "Thickness"))
    links.new(combine_cube_translation.inputs["Z"], translate_z.outputs["Value"])
    links.new(
        _node_socket(transform_cube, "INPUT", "Geometry", index=0),
        _node_socket(cube, "OUTPUT", "Mesh", "Geometry", index=0),
    )
    links.new(
        _node_socket(transform_cube, "INPUT", "Translation", index=1),
        _node_socket(combine_cube_translation, "OUTPUT", "Vector", index=0),
    )
    links.new(
        _node_socket(transform_cube, "INPUT", "Scale", index=3),
        _node_socket(combine_base_scale, "OUTPUT", "Vector", index=0),
    )

    random_xy.inputs["Min"].default_value = 0.0
    random_xy.inputs["Max"].default_value = 1.0
    random_z.inputs["Min"].default_value = 0.0
    random_z.inputs["Max"].default_value = 1.0
    links.new(
        _node_socket(random_id_xy, "INPUT", "Value", index=0),
        _node_socket(group_input, "OUTPUT", "Seed"),
    )
    links.new(
        _node_socket(random_id_z, "INPUT", "Value", index=0),
        _node_socket(group_input, "OUTPUT", "Seed"),
    )
    links.new(
        _node_socket(random_id_rot, "INPUT", "Value", index=0),
        _node_socket(group_input, "OUTPUT", "Seed"),
    )
    try:
        links.new(
            _node_socket(random_id_xy, "INPUT", "Value", index=1),
            _node_socket(point_index, "OUTPUT", "Index", index=0),
        )
        links.new(
            _node_socket(random_id_z, "INPUT", "Value", index=1),
            _node_socket(point_index, "OUTPUT", "Index", index=0),
        )
        links.new(
            _node_socket(random_id_rot, "INPUT", "Value", index=1),
            _node_socket(point_index, "OUTPUT", "Index", index=0),
        )
    except Exception:
        pass
    try:
        links.new(
            _node_socket(random_xy, "INPUT", "ID", "Seed", index=7),
            _node_socket(random_id_xy, "OUTPUT", "Value", index=0),
        )
        links.new(
            _node_socket(random_z, "INPUT", "ID", "Seed", index=7),
            _node_socket(random_id_z, "OUTPUT", "Value", index=0),
        )
        links.new(
            _node_socket(random_rot, "INPUT", "ID", "Seed", index=7),
            _node_socket(random_id_rot, "OUTPUT", "Value", index=0),
        )
    except Exception:
        pass

    links.new(subtract_xy.inputs[1], _node_socket(group_input, "OUTPUT", "Scale Jitter"))
    links.new(add_xy.inputs[0], subtract_xy.outputs["Value"])
    links.new(add_xy.inputs[1], random_xy.outputs["Value"])
    links.new(
        row_overlap_scale.inputs[1],
        _node_socket(group_input, "OUTPUT", "Row Overlap"),
    )
    links.new(overlap_y_scale.inputs[0], add_xy.outputs["Value"])
    links.new(overlap_y_scale.inputs[1], row_overlap_scale.outputs["Value"])
    links.new(subtract_z.inputs[1], _node_socket(group_input, "OUTPUT", "Thickness Jitter"))
    links.new(add_z.inputs[0], subtract_z.outputs["Value"])
    links.new(add_z.inputs[1], random_z.outputs["Value"])
    links.new(
        _node_socket(negate_rotation, "INPUT", "Value", index=0),
        _node_socket(group_input, "OUTPUT", "Rotation Jitter"),
    )
    links.new(
        _node_socket(random_rot, "INPUT", "Min", index=2),
        _node_socket(negate_rotation, "OUTPUT", "Value", index=0),
    )
    links.new(
        _node_socket(random_rot, "INPUT", "Max", index=3),
        _node_socket(group_input, "OUTPUT", "Rotation Jitter"),
    )

    links.new(combine_instance_scale.inputs["X"], add_xy.outputs["Value"])
    links.new(combine_instance_scale.inputs["Y"], overlap_y_scale.outputs["Value"])
    links.new(combine_instance_scale.inputs["Z"], add_z.outputs["Value"])
    links.new(combine_twist.inputs["Z"], random_rot.outputs["Value"])

    links.new(
        _node_socket(instance_on_points, "INPUT", "Points", "Geometry", index=0),
        _node_socket(set_position, "OUTPUT", "Geometry", index=0),
    )
    links.new(
        _node_socket(instance_on_points, "INPUT", "Instance", index=2),
        _node_socket(transform_cube, "OUTPUT", "Geometry", index=0),
    )
    try:
        links.new(
            _node_socket(instance_on_points, "INPUT", "Rotation"),
            _node_socket(align_to_normal, "OUTPUT", "Rotation", index=0),
        )
    except Exception:
        links.new(
            _node_socket(instance_on_points, "INPUT", "Rotation", index=5),
            _node_socket(align_to_normal, "OUTPUT", "Rotation", index=0),
        )
    links.new(
        _node_socket(scale_instances, "INPUT", "Instances", "Geometry", index=0),
        _node_socket(instance_on_points, "OUTPUT", "Instances", "Geometry", index=0),
    )
    links.new(
        _node_socket(scale_instances, "INPUT", "Scale", index=2),
        _node_socket(combine_instance_scale, "OUTPUT", "Vector", index=0),
    )
    links.new(
        _node_socket(rotate_instances, "INPUT", "Instances", "Geometry", index=0),
        _node_socket(scale_instances, "OUTPUT", "Instances", "Geometry", index=0),
    )
    try:
        links.new(
            _node_socket(rotate_instances, "INPUT", "Rotation", index=3),
            _node_socket(combine_twist, "OUTPUT", "Vector", index=0),
        )
    except Exception:
        pass
    links.new(
        _node_socket(realize_instances, "INPUT", "Geometry", index=0),
        _node_socket(rotate_instances, "OUTPUT", "Instances", "Geometry", index=0),
    )
    links.new(
        _node_socket(join_geometry, "INPUT", "Geometry", index=0),
        _node_socket(group_input, "OUTPUT", "Geometry", index=0),
    )
    links.new(
        _node_socket(join_geometry, "INPUT", "Geometry", index=1),
        _node_socket(realize_instances, "OUTPUT", "Geometry", index=0),
    )
    links.new(
        _node_socket(group_output, "INPUT", "Geometry", index=0),
        _node_socket(join_geometry, "OUTPUT", "Geometry", index=0),
    )

    node_group["cd_shingle_group_version"] = SHINGLE_GROUP_VERSION


def _get_dev_override_path():
    return os.environ.get("BLENDER_COLLECTION_DEFORMER_DEV_FILE", DEFAULT_DEV_OVERRIDE_PATH)


def _load_dev_override_module():
    path = _get_dev_override_path()
    DEV_OVERRIDE_STATE["path"] = path

    if not path or not os.path.isfile(path):
        DEV_OVERRIDE_STATE["module"] = None
        DEV_OVERRIDE_STATE["mtime"] = None
        DEV_OVERRIDE_STATE["error"] = ""
        return None

    mtime = os.path.getmtime(path)
    if (
        DEV_OVERRIDE_STATE["module"] is not None
        and DEV_OVERRIDE_STATE["path"] == path
        and DEV_OVERRIDE_STATE["mtime"] == mtime
    ):
        return DEV_OVERRIDE_STATE["module"]

    try:
        spec = importlib.util.spec_from_file_location(
            "cd_wood_shingles_dev_override",
            path,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load dev override from '{path}'.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        DEV_OVERRIDE_STATE["module"] = module
        DEV_OVERRIDE_STATE["mtime"] = mtime
        DEV_OVERRIDE_STATE["error"] = ""
        return module
    except Exception as exc:
        DEV_OVERRIDE_STATE["module"] = None
        DEV_OVERRIDE_STATE["mtime"] = mtime
        DEV_OVERRIDE_STATE["error"] = str(exc)
        raise


def _get_shingle_dev_stamp():
    module = _load_dev_override_module()
    if module is None or not hasattr(module, "build_wood_shingles_node_group"):
        return ""
    return f"{DEV_OVERRIDE_STATE['path']}|{DEV_OVERRIDE_STATE['mtime']}"


def _build_wood_shingles_node_group(node_group):
    module = _load_dev_override_module()
    if module is not None and hasattr(module, "build_wood_shingles_node_group"):
        api = {
            "_clear_node_group_interface": _clear_node_group_interface,
            "_add_socket": _add_socket,
            "_find_interface_socket": _find_interface_socket,
            "_new_node": _new_node,
            "_node_socket": _node_socket,
            "build_default_wood_shingles_node_group": _build_wood_shingles_node_group_default,
            "math": math,
            "SHINGLE_GROUP_VERSION": SHINGLE_GROUP_VERSION,
        }
        module.build_wood_shingles_node_group(node_group, api)
        node_group["cd_shingle_group_version"] = SHINGLE_GROUP_VERSION
        node_group["cd_shingle_dev_stamp"] = _get_shingle_dev_stamp()
        return

    _build_wood_shingles_node_group_default(node_group)
    node_group["cd_shingle_dev_stamp"] = ""


def rebuild_wood_shingles_node_group():
    node_group = bpy.data.node_groups.get(SHINGLE_NODE_GROUP_NAME)
    if node_group is None or node_group.bl_idname != "GeometryNodeTree":
        node_group = bpy.data.node_groups.new(SHINGLE_NODE_GROUP_NAME, "GeometryNodeTree")
    _build_wood_shingles_node_group(node_group)
    return node_group


def ensure_wood_shingles_node_group():
    dev_stamp = _get_shingle_dev_stamp()
    node_group = bpy.data.node_groups.get(SHINGLE_NODE_GROUP_NAME)
    if node_group is None or node_group.bl_idname != "GeometryNodeTree":
        node_group = bpy.data.node_groups.new(SHINGLE_NODE_GROUP_NAME, "GeometryNodeTree")
        _build_wood_shingles_node_group(node_group)
        return node_group

    if (
        node_group.get("cd_shingle_group_version") != SHINGLE_GROUP_VERSION
        or node_group.get("cd_shingle_dev_stamp", "") != dev_stamp
    ):
        _build_wood_shingles_node_group(node_group)

    return node_group


def ensure_host_object(host_name=None, target_collection=None):
    obj = bpy.data.objects.get(host_name) if host_name else None
    if obj and obj.type in {"MESH", "CURVE", "SURFACE", "FONT", "CURVES"}:
        return obj

    if host_name and obj is not None and obj.type not in {"MESH", "CURVE", "SURFACE", "FONT", "CURVES"}:
        raise ValueError(f"Object '{host_name}' exists but is not a supported host type.")

    mesh_name = f"{host_name or 'CollectionDeformHost'}Mesh"
    object_name = host_name or "CollectionDeformHost"
    mesh = bpy.data.meshes.new(mesh_name)
    obj = bpy.data.objects.new(object_name, mesh)

    link_collection = target_collection or bpy.context.scene.collection
    link_collection.objects.link(obj)
    obj.location = bpy.context.scene.cursor.location
    return obj


def ensure_modifier(obj, node_group):
    modifier = obj.modifiers.get(MODIFIER_NAME)
    if modifier is None or modifier.type != "NODES":
        modifier = obj.modifiers.new(name=MODIFIER_NAME, type="NODES")
    modifier.node_group = node_group
    return modifier


def ensure_named_modifier(obj, node_group, modifier_name):
    modifier = obj.modifiers.get(modifier_name)
    if modifier is None or modifier.type != "NODES":
        modifier = obj.modifiers.new(name=modifier_name, type="NODES")
    modifier.node_group = node_group
    return modifier


def set_modifier_input(modifier, node_group, socket_name, value):
    interface_socket = _find_interface_socket(node_group, socket_name, "INPUT")
    if interface_socket is None:
        return

    identifier = getattr(interface_socket, "identifier", socket_name)
    modifier[identifier] = value


def apply_collection_deformer(
    *,
    collection_name,
    host_object_name=None,
    host_collection_name=None,
    strength=0.35,
    noise_scale=1.5,
    translation=(0.0, 0.0, 0.0),
    scale=(1.0, 1.0, 1.0),
):
    source_collection = bpy.data.collections.get(collection_name)
    if source_collection is None:
        raise ValueError(f"Collection '{collection_name}' was not found.")

    target_collection = None
    if host_collection_name:
        target_collection = bpy.data.collections.get(host_collection_name)
        if target_collection is None:
            raise ValueError(f"Host collection '{host_collection_name}' was not found.")

    node_group = ensure_node_group()
    host = ensure_host_object(host_object_name, target_collection)
    modifier = ensure_modifier(host, node_group)

    set_modifier_input(modifier, node_group, "Collection", source_collection)
    set_modifier_input(modifier, node_group, "Strength", float(strength))
    set_modifier_input(modifier, node_group, "Noise Scale", float(noise_scale))
    set_modifier_input(modifier, node_group, "Translation", tuple(translation))
    set_modifier_input(modifier, node_group, "Scale", tuple(scale))

    host.update_tag()
    bpy.context.view_layer.update()

    return {
        "host_object": host.name,
        "modifier": modifier.name,
        "node_group": node_group.name,
        "collection": source_collection.name,
        "strength": float(strength),
        "noise_scale": float(noise_scale),
        "translation": list(translation),
        "scale": list(scale),
    }


def apply_wood_shingles(
    *,
    target_object_name,
    columns=8,
    rows=8,
    tile_size=0.18,
    thickness=0.025,
    scale_jitter=0.12,
    thickness_jitter=0.35,
    rotation_jitter_degrees=10.0,
    surface_offset=0.012,
    row_overlap=0.18,
    seed=0,
):
    target_object = bpy.data.objects.get(target_object_name)
    if target_object is None:
        raise ValueError(f"Object '{target_object_name}' was not found.")
    if target_object.type != "MESH":
        raise ValueError(f"Object '{target_object_name}' must be a mesh.")

    node_group = ensure_wood_shingles_node_group()
    modifier = ensure_named_modifier(target_object, node_group, SHINGLE_MODIFIER_NAME)

    set_modifier_input(modifier, node_group, "Columns", int(columns))
    set_modifier_input(modifier, node_group, "Rows", int(rows))
    set_modifier_input(modifier, node_group, "Tile Size", float(tile_size))
    set_modifier_input(modifier, node_group, "Thickness", float(thickness))
    set_modifier_input(modifier, node_group, "Scale Jitter", float(scale_jitter))
    set_modifier_input(modifier, node_group, "Thickness Jitter", float(thickness_jitter))
    set_modifier_input(
        modifier,
        node_group,
        "Rotation Jitter",
        math.radians(float(rotation_jitter_degrees)),
    )
    set_modifier_input(modifier, node_group, "Surface Offset", float(surface_offset))
    set_modifier_input(modifier, node_group, "Row Overlap", float(row_overlap))
    set_modifier_input(modifier, node_group, "Seed", int(seed))

    target_object.update_tag()
    bpy.context.view_layer.update()

    return {
        "target_object": target_object.name,
        "modifier": modifier.name,
        "node_group": node_group.name,
        "columns": int(columns),
        "rows": int(rows),
        "tile_size": float(tile_size),
        "thickness": float(thickness),
        "scale_jitter": float(scale_jitter),
        "thickness_jitter": float(thickness_jitter),
        "rotation_jitter_degrees": float(rotation_jitter_degrees),
        "surface_offset": float(surface_offset),
        "row_overlap": float(row_overlap),
        "seed": int(seed),
    }


def _decode_json_body(request):
    if not request["body"]:
        return {}
    try:
        return json.loads(request["body"].decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON body: {exc}") from exc


def _json_response(status, payload):
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    reason = {
        200: "OK",
        202: "Accepted",
        400: "Bad Request",
        401: "Unauthorized",
        404: "Not Found",
        405: "Method Not Allowed",
        413: "Payload Too Large",
        500: "Internal Server Error",
    }.get(status, "OK")
    header = (
        f"HTTP/1.1 {status} {reason}\r\n"
        "Content-Type: application/json; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "Access-Control-Allow-Headers: Content-Type, Authorization, X-Bridge-Token\r\n"
        "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
        "\r\n"
    ).encode("utf-8")
    return header + body


def _unauthorized_response():
    return _json_response(
        401,
        {
            "ok": False,
            "error": "Unauthorized",
            "hint": "Provide the bridge token in X-Bridge-Token or Authorization: Bearer <token>.",
        },
    )


def _extract_token(headers):
    auth_header = headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return headers.get("x-bridge-token", "").strip()


def _require_token(request):
    token = BRIDGE_STATE["token"].strip()
    if not token:
        return False
    request_token = _extract_token(request["headers"])
    return request_token != token


def _list_scene_state():
    return {
        "collections": sorted(collection.name for collection in bpy.data.collections),
        "objects": sorted(obj.name for obj in bpy.data.objects),
        "node_groups": sorted(group.name for group in bpy.data.node_groups),
    }


def _dispatch_request(request):
    path = urlsplit(request["target"]).path

    if request["method"] == "OPTIONS":
        return _json_response(200, {"ok": True})

    if path != "/health" and _require_token(request):
        return _unauthorized_response()

    if request["method"] == "GET" and path == "/health":
        return _json_response(
            200,
            {
                "ok": True,
                "service": "collection-deformer-bridge",
                "host": BRIDGE_STATE["host"],
                "port": BRIDGE_STATE["port"],
                "has_token": bool(BRIDGE_STATE["token"]),
                "scene": bpy.context.scene.name if bpy.context.scene else None,
            },
        )

    if request["method"] == "GET" and path == "/v1/scene":
        return _json_response(200, {"ok": True, "scene": _list_scene_state()})

    if request["method"] == "POST" and path == "/v1/collection-deformer":
        payload = _decode_json_body(request)
        result = apply_collection_deformer(
            collection_name=payload.get("collection", ""),
            host_object_name=payload.get("host_object"),
            host_collection_name=payload.get("host_collection"),
            strength=payload.get("strength", 0.35),
            noise_scale=payload.get("noise_scale", 1.5),
            translation=payload.get("translation", (0.0, 0.0, 0.0)),
            scale=payload.get("scale", (1.0, 1.0, 1.0)),
        )
        return _json_response(200, {"ok": True, "result": result})

    if request["method"] == "POST" and path == "/v1/wood-shingles":
        payload = _decode_json_body(request)
        result = apply_wood_shingles(
            target_object_name=payload.get("target_object", ""),
            columns=payload.get("columns", payload.get("density", 8)),
            rows=payload.get("rows", payload.get("density", 8)),
            tile_size=payload.get("tile_size", 0.18),
            thickness=payload.get("thickness", 0.025),
            scale_jitter=payload.get("scale_jitter", 0.12),
            thickness_jitter=payload.get("thickness_jitter", 0.35),
            rotation_jitter_degrees=payload.get("rotation_jitter_degrees", 10.0),
            surface_offset=payload.get("surface_offset", 0.012),
            row_overlap=payload.get("row_overlap", 0.18),
            seed=payload.get("seed", 0),
        )
        return _json_response(200, {"ok": True, "result": result})

    if request["method"] == "GET" and path == "/v1/dev/status":
        dev_stamp = _get_shingle_dev_stamp()
        return _json_response(
            200,
            {
                "ok": True,
                "dev_override_path": DEV_OVERRIDE_STATE["path"],
                "dev_override_loaded": bool(dev_stamp),
                "dev_override_error": DEV_OVERRIDE_STATE["error"],
                "dev_override_stamp": dev_stamp,
            },
        )

    if request["method"] == "POST" and path == "/v1/dev/rebuild-wood-shingles":
        payload = _decode_json_body(request)
        node_group = rebuild_wood_shingles_node_group()
        target_object_name = payload.get("target_object", "")
        if target_object_name:
            target_object = bpy.data.objects.get(target_object_name)
            if target_object is None:
                raise ValueError(f"Object '{target_object_name}' was not found.")
            if target_object.type != "MESH":
                raise ValueError(f"Object '{target_object_name}' must be a mesh.")
            modifier = ensure_named_modifier(target_object, node_group, SHINGLE_MODIFIER_NAME)
            modifier.node_group = node_group
            target_object.update_tag()
        bpy.context.view_layer.update()
        return _json_response(
            200,
            {
                "ok": True,
                "node_group": node_group.name,
                "dev_override_path": DEV_OVERRIDE_STATE["path"],
                "dev_override_loaded": bool(_get_shingle_dev_stamp()),
                "dev_override_error": DEV_OVERRIDE_STATE["error"],
            },
        )

    if request["method"] == "POST" and path == "/v1/server/stop":
        BRIDGE_STATE["stop_requested"] = True
        return _json_response(202, {"ok": True, "message": "Bridge stop requested."})

    return _json_response(
        404,
        {
            "ok": False,
            "error": "Not Found",
            "path": path,
        },
    )


def _close_client(client_key):
    client_state = BRIDGE_STATE["clients"].pop(client_key, None)
    if client_state is None:
        return
    try:
        client_state["socket"].close()
    except OSError:
        pass


def _try_parse_request(buffer):
    header_end = buffer.find(b"\r\n\r\n")
    if header_end == -1:
        if len(buffer) > MAX_REQUEST_SIZE:
            raise ValueError("HTTP header exceeds max request size.")
        return None

    header_blob = bytes(buffer[:header_end]).decode("iso-8859-1")
    header_lines = header_blob.split("\r\n")
    if not header_lines:
        raise ValueError("Empty HTTP request.")

    try:
        method, target, version = header_lines[0].split(" ", 2)
    except ValueError as exc:
        raise ValueError("Malformed HTTP request line.") from exc

    headers = {}
    for line in header_lines[1:]:
        if not line:
            continue
        if ":" not in line:
            raise ValueError(f"Malformed HTTP header: {line}")
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()

    content_length = int(headers.get("content-length", "0") or "0")
    total_length = header_end + 4 + content_length
    if total_length > MAX_REQUEST_SIZE:
        raise ValueError("HTTP body exceeds max request size.")
    if len(buffer) < total_length:
        return None

    body = bytes(buffer[header_end + 4 : total_length])
    del buffer[:total_length]

    return {
        "method": method.upper(),
        "target": target,
        "version": version,
        "headers": headers,
        "body": body,
    }


def _service_client(client_key, client_state):
    conn = client_state["socket"]
    try:
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                _close_client(client_key)
                return
            client_state["buffer"].extend(chunk)
            if len(client_state["buffer"]) > MAX_REQUEST_SIZE:
                conn.sendall(_json_response(413, {"ok": False, "error": "Request too large."}))
                _close_client(client_key)
                return
    except BlockingIOError:
        pass
    except OSError:
        _close_client(client_key)
        return

    try:
        request = _try_parse_request(client_state["buffer"])
    except ValueError as exc:
        conn.sendall(_json_response(400, {"ok": False, "error": str(exc)}))
        _close_client(client_key)
        return

    if request is None:
        return

    try:
        response = _dispatch_request(request)
    except ValueError as exc:
        response = _json_response(400, {"ok": False, "error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        response = _json_response(
            500,
            {
                "ok": False,
                "error": str(exc),
                "type": exc.__class__.__name__,
                "traceback": traceback.format_exc(),
            },
        )

    try:
        conn.sendall(response)
    finally:
        _close_client(client_key)


def _accept_new_clients():
    server_socket = BRIDGE_STATE["server_socket"]
    if server_socket is None:
        return
    while True:
        try:
            conn, addr = server_socket.accept()
        except BlockingIOError:
            break
        except OSError:
            break
        conn.setblocking(False)
        BRIDGE_STATE["clients"][id(conn)] = {
            "socket": conn,
            "address": addr,
            "buffer": bytearray(),
        }


def _bridge_timer():
    if BRIDGE_STATE["server_socket"] is None:
        BRIDGE_STATE["timer_registered"] = False
        return None

    _accept_new_clients()
    for client_key, client_state in list(BRIDGE_STATE["clients"].items()):
        _service_client(client_key, client_state)

    if BRIDGE_STATE["stop_requested"]:
        stop_bridge_server()
        return None

    return BRIDGE_TIMER_INTERVAL


def start_bridge_server(host, port, token=""):
    if BRIDGE_STATE["server_socket"] is not None:
        raise RuntimeError("Bridge server is already running.")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, int(port)))
    server_socket.listen(16)
    server_socket.setblocking(False)

    BRIDGE_STATE["server_socket"] = server_socket
    BRIDGE_STATE["host"] = host
    BRIDGE_STATE["port"] = int(port)
    BRIDGE_STATE["token"] = token.strip()
    BRIDGE_STATE["stop_requested"] = False

    if not BRIDGE_STATE["timer_registered"]:
        bpy.app.timers.register(_bridge_timer)
        BRIDGE_STATE["timer_registered"] = True


def stop_bridge_server():
    for client_key in list(BRIDGE_STATE["clients"].keys()):
        _close_client(client_key)

    server_socket = BRIDGE_STATE["server_socket"]
    if server_socket is not None:
        try:
            server_socket.close()
        except OSError:
            pass

    BRIDGE_STATE["server_socket"] = None
    BRIDGE_STATE["stop_requested"] = False
    BRIDGE_STATE["token"] = ""
    BRIDGE_STATE["timer_registered"] = False


def bridge_is_running():
    return BRIDGE_STATE["server_socket"] is not None


class CollectionDeformSettings(PropertyGroup):
    pass


class WM_OT_start_bridge_server(Operator):
    bl_idname = "wm.start_collection_bridge_server"
    bl_label = "Start HTTP Bridge"
    bl_description = "Start the embedded HTTP bridge"

    def execute(self, context):
        try:
            start_bridge_server(DEFAULT_BRIDGE_HOST, DEFAULT_BRIDGE_PORT, "")
        except OSError as exc:
            self.report({"ERROR"}, f"Could not start bridge: {exc}")
            return {"CANCELLED"}
        except RuntimeError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        self.report(
            {"INFO"},
            f"HTTP bridge listening on http://{DEFAULT_BRIDGE_HOST}:{DEFAULT_BRIDGE_PORT}",
        )
        return {"FINISHED"}


class WM_OT_stop_bridge_server(Operator):
    bl_idname = "wm.stop_collection_bridge_server"
    bl_label = "Stop HTTP Bridge"
    bl_description = "Stop the embedded HTTP bridge"

    def execute(self, context):
        if not bridge_is_running():
            self.report({"WARNING"}, "Bridge is not running.")
            return {"CANCELLED"}

        stop_bridge_server()
        self.report({"INFO"}, "HTTP bridge stopped.")
        return {"FINISHED"}


class VIEW3D_PT_collection_deformer(Panel):
    bl_label = "HTTP Bridge"
    bl_idname = "VIEW3D_PT_collection_deformer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Collection Deform"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        if bridge_is_running():
            row.operator("wm.stop_collection_bridge_server", icon="CANCEL")
        else:
            row.operator("wm.start_collection_bridge_server", icon="PLAY")

        layout.separator()
        layout.label(text=f"http://{DEFAULT_BRIDGE_HOST}:{DEFAULT_BRIDGE_PORT}")
        layout.label(text="POST /v1/collection-deformer")
        layout.label(text="POST /v1/wood-shingles")


class SCENE_PT_collection_deformer_bridge(Panel):
    bl_label = "Collection Deformer Bridge"
    bl_idname = "SCENE_PT_collection_deformer_bridge"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        if bridge_is_running():
            row.operator("wm.stop_collection_bridge_server", icon="CANCEL")
        else:
            row.operator("wm.start_collection_bridge_server", icon="PLAY")

        layout.separator()
        status = (
            f"Running: http://{BRIDGE_STATE['host']}:{BRIDGE_STATE['port']}"
            if bridge_is_running()
            else "Stopped"
        )
        layout.label(text=status)
        layout.label(text="Endpoints:")
        layout.label(text="/health")
        layout.label(text="/v1/scene")
        layout.label(text="/v1/collection-deformer")
        layout.label(text="/v1/wood-shingles")


CLASSES = (
    CollectionDeformSettings,
    WM_OT_start_bridge_server,
    WM_OT_stop_bridge_server,
    VIEW3D_PT_collection_deformer,
    SCENE_PT_collection_deformer_bridge,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)

    bpy.types.Scene.collection_deform_settings = PointerProperty(
        type=CollectionDeformSettings
    )


def unregister():
    stop_bridge_server()

    if hasattr(bpy.types.Scene, "collection_deform_settings"):
        del bpy.types.Scene.collection_deform_settings

    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

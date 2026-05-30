"""
Multi-face shingle build.

This keeps the single-face shingle chain intact inside each roof branch:
local UV grid, UV surface sampling, per-branch average normal, instances,
light variation, overlap, then one final join with the source geometry.
"""


def build_wood_shingles_node_group(node_group, api):
    clear_interface = api["_clear_node_group_interface"]
    add_socket = api["_add_socket"]
    new_node = api["_new_node"]
    node_socket = api["_node_socket"]
    shingle_group_version = api["SHINGLE_GROUP_VERSION"]

    node_group.nodes.clear()
    node_group.links.clear()
    clear_interface(node_group)

    if hasattr(node_group, "is_modifier"):
        node_group.is_modifier = True

    add_socket(node_group, "Geometry", "INPUT", "NodeSocketGeometry")
    add_socket(node_group, "Columns", "INPUT", "NodeSocketInt", default_value=18, min_value=1, max_value=10000)
    add_socket(node_group, "Rows", "INPUT", "NodeSocketInt", default_value=18, min_value=1, max_value=10000)
    add_socket(node_group, "Tile Size", "INPUT", "NodeSocketFloat", default_value=0.11, min_value=0.001, max_value=100.0)
    add_socket(node_group, "Thickness", "INPUT", "NodeSocketFloat", default_value=0.022, min_value=0.001, max_value=10.0)
    add_socket(node_group, "Scale Jitter", "INPUT", "NodeSocketFloat", default_value=0.06, min_value=0.0, max_value=1.0)
    add_socket(node_group, "Thickness Jitter", "INPUT", "NodeSocketFloat", default_value=0.12, min_value=0.0, max_value=1.0)
    add_socket(node_group, "Rotation Jitter", "INPUT", "NodeSocketFloat", default_value=0.035, min_value=0.0, max_value=3.14159)
    add_socket(node_group, "Surface Offset", "INPUT", "NodeSocketFloat", default_value=0.003, min_value=0.0, max_value=10.0)
    add_socket(node_group, "Top Face Threshold", "INPUT", "NodeSocketFloat", default_value=0.0, min_value=-1.0, max_value=1.0)
    add_socket(node_group, "Row Overlap", "INPUT", "NodeSocketFloat", default_value=0.12, min_value=0.0, max_value=1.0)
    add_socket(node_group, "Seed", "INPUT", "NodeSocketInt", default_value=0, min_value=-2147483648, max_value=2147483647)
    add_socket(node_group, "Geometry", "OUTPUT", "NodeSocketGeometry")

    nodes = node_group.nodes
    links = node_group.links

    group_input = new_node(nodes, "NodeGroupInput")
    group_input.location = (-3000, 0)

    group_output = new_node(nodes, "NodeGroupOutput")
    group_output.location = (4200, -120)

    input_normal = new_node(nodes, "GeometryNodeInputNormal")
    input_normal.location = (-2780, -260)

    separate_normal = new_node(nodes, "ShaderNodeSeparateXYZ")
    separate_normal.location = (-2560, -260)

    compare_up = new_node(nodes, "FunctionNodeCompare")
    compare_up.location = (-2340, -180)
    compare_up.data_type = "FLOAT"
    compare_up.operation = "GREATER_THAN"

    compare_x = new_node(nodes, "FunctionNodeCompare")
    compare_x.location = (-2340, -320)
    compare_x.data_type = "FLOAT"
    compare_x.operation = "GREATER_THAN"

    compare_y = new_node(nodes, "FunctionNodeCompare")
    compare_y.location = (-2340, -440)
    compare_y.data_type = "FLOAT"
    compare_y.operation = "GREATER_THAN"

    roof_up = new_node(nodes, "GeometryNodeSeparateGeometry")
    roof_up.location = (-2120, 0)
    try:
        roof_up.domain = "FACE"
    except Exception:
        pass

    x_split = new_node(nodes, "GeometryNodeSeparateGeometry")
    x_split.location = (-1900, 0)
    try:
        x_split.domain = "FACE"
    except Exception:
        pass

    xp_split = new_node(nodes, "GeometryNodeSeparateGeometry")
    xp_split.location = (-1680, -120)
    try:
        xp_split.domain = "FACE"
    except Exception:
        pass

    xn_split = new_node(nodes, "GeometryNodeSeparateGeometry")
    xn_split.location = (-1680, 120)
    try:
        xn_split.domain = "FACE"
    except Exception:
        pass

    links.new(node_socket(separate_normal, "INPUT", "Vector", index=0), node_socket(input_normal, "OUTPUT", "Normal", index=0))
    links.new(node_socket(compare_up, "INPUT", "A", index=2), node_socket(separate_normal, "OUTPUT", "Z"))
    links.new(node_socket(compare_up, "INPUT", "B", index=3), node_socket(group_input, "OUTPUT", "Top Face Threshold"))
    links.new(node_socket(compare_x, "INPUT", "A", index=2), node_socket(separate_normal, "OUTPUT", "X"))
    links.new(node_socket(compare_y, "INPUT", "A", index=2), node_socket(separate_normal, "OUTPUT", "Y"))
    links.new(node_socket(roof_up, "INPUT", "Geometry", index=0), node_socket(group_input, "OUTPUT", "Geometry", index=0))
    links.new(node_socket(roof_up, "INPUT", "Selection", index=1), node_socket(compare_up, "OUTPUT", "Result", index=0))
    links.new(node_socket(x_split, "INPUT", "Geometry", index=0), node_socket(roof_up, "OUTPUT", "Selection", index=0))
    links.new(node_socket(x_split, "INPUT", "Selection", index=1), node_socket(compare_x, "OUTPUT", "Result", index=0))
    links.new(node_socket(xp_split, "INPUT", "Geometry", index=0), node_socket(x_split, "OUTPUT", "Selection", index=0))
    links.new(node_socket(xp_split, "INPUT", "Selection", index=1), node_socket(compare_y, "OUTPUT", "Result", index=0))
    links.new(node_socket(xn_split, "INPUT", "Geometry", index=0), node_socket(x_split, "OUTPUT", "Inverted", index=1))
    links.new(node_socket(xn_split, "INPUT", "Selection", index=1), node_socket(compare_y, "OUTPUT", "Result", index=0))

    def link(input_socket, output_socket):
        links.new(input_socket, output_socket)

    roof_bounds = new_node(nodes, "GeometryNodeBoundBox")
    roof_bounds.location = (-1900, -520)

    roof_bounds_size = new_node(nodes, "ShaderNodeVectorMath")
    roof_bounds_size.location = (-1660, -520)
    roof_bounds_size.operation = "SUBTRACT"

    split_roof_bounds_size = new_node(nodes, "ShaderNodeSeparateXYZ")
    split_roof_bounds_size.location = (-1420, -520)

    link(node_socket(roof_bounds, "INPUT", "Geometry", index=0), node_socket(roof_up, "OUTPUT", "Selection", index=0))
    link(node_socket(roof_bounds_size, "INPUT", "Vector", index=0), node_socket(roof_bounds, "OUTPUT", "Max", index=2))
    link(node_socket(roof_bounds_size, "INPUT", "Vector", index=1), node_socket(roof_bounds, "OUTPUT", "Min", index=1))
    link(node_socket(split_roof_bounds_size, "INPUT", "Vector", index=0), node_socket(roof_bounds_size, "OUTPUT", "Vector", index=0))

    face_area = new_node(nodes, "GeometryNodeInputMeshFaceArea")
    face_area.location = (-1900, -820)

    roof_area = new_node(nodes, "GeometryNodeAttributeStatistic")
    roof_area.location = (-1660, -820)
    roof_area.data_type = "FLOAT"
    try:
        roof_area.domain = "FACE"
    except Exception:
        pass

    safe_roof_area = new_node(nodes, "ShaderNodeMath")
    safe_roof_area.location = (-1420, -820)
    safe_roof_area.operation = "MAXIMUM"
    safe_roof_area.inputs[1].default_value = 0.0001

    link(node_socket(roof_area, "INPUT", "Geometry", index=0), node_socket(roof_up, "OUTPUT", "Selection", index=0))
    link(node_socket(roof_area, "INPUT", "Attribute", index=2), node_socket(face_area, "OUTPUT", "Area", index=0))
    link(safe_roof_area.inputs[0], node_socket(roof_area, "OUTPUT", "Sum", index=2))

    def build_branch(branch_geometry, origin_x, origin_y, branch_seed_offset, swap_uv=False):
        bool_true = new_node(nodes, "FunctionNodeInputBool")
        bool_true.location = (origin_x, origin_y + 180)
        bool_true.boolean = True

        bool_false = new_node(nodes, "FunctionNodeInputBool")
        bool_false.location = (origin_x, origin_y + 300)
        bool_false.boolean = False

        bounds = new_node(nodes, "GeometryNodeBoundBox")
        bounds.location = (origin_x, origin_y - 160)

        bounds_size = new_node(nodes, "ShaderNodeVectorMath")
        bounds_size.location = (origin_x + 240, origin_y - 120)
        bounds_size.operation = "SUBTRACT"

        split_bounds_size = new_node(nodes, "ShaderNodeSeparateXYZ")
        split_bounds_size.location = (origin_x + 480, origin_y - 120)

        column_extent_socket_name = "Y" if swap_uv else "X"
        row_extent_socket_name = "X" if swap_uv else "Y"

        one_minus_overlap = new_node(nodes, "ShaderNodeMath")
        one_minus_overlap.location = (origin_x + 480, origin_y - 520)
        one_minus_overlap.operation = "SUBTRACT"
        one_minus_overlap.inputs[0].default_value = 1.0

        row_pitch = new_node(nodes, "ShaderNodeMath")
        row_pitch.location = (origin_x + 720, origin_y - 520)
        row_pitch.operation = "MULTIPLY"

        safe_roof_column_extent = new_node(nodes, "ShaderNodeMath")
        safe_roof_column_extent.location = (origin_x + 720, origin_y + 20)
        safe_roof_column_extent.operation = "MAXIMUM"
        safe_roof_column_extent.inputs[1].default_value = 0.0001

        safe_roof_row_extent = new_node(nodes, "ShaderNodeMath")
        safe_roof_row_extent.location = (origin_x + 720, origin_y - 80)
        safe_roof_row_extent.operation = "MAXIMUM"
        safe_roof_row_extent.inputs[1].default_value = 0.0001

        auto_columns_float = new_node(nodes, "ShaderNodeMath")
        auto_columns_float.location = (origin_x + 720, origin_y - 120)
        auto_columns_float.operation = "DIVIDE"

        auto_rows_float = new_node(nodes, "ShaderNodeMath")
        auto_rows_float.location = (origin_x + 720, origin_y - 220)
        auto_rows_float.operation = "DIVIDE"

        scaled_columns_float = new_node(nodes, "ShaderNodeMath")
        scaled_columns_float.location = (origin_x + 860, origin_y - 120)
        scaled_columns_float.operation = "MULTIPLY"

        scaled_rows_float = new_node(nodes, "ShaderNodeMath")
        scaled_rows_float.location = (origin_x + 860, origin_y - 220)
        scaled_rows_float.operation = "MULTIPLY"

        min_columns = new_node(nodes, "ShaderNodeMath")
        min_columns.location = (origin_x + 960, origin_y - 120)
        min_columns.operation = "MAXIMUM"
        min_columns.inputs[1].default_value = 1.0

        min_rows = new_node(nodes, "ShaderNodeMath")
        min_rows.location = (origin_x + 960, origin_y - 220)
        min_rows.operation = "MAXIMUM"
        min_rows.inputs[1].default_value = 1.0

        columns_to_int = new_node(nodes, "FunctionNodeFloatToInt")
        columns_to_int.location = (origin_x + 1200, origin_y - 120)
        try:
            columns_to_int.rounding_mode = "CEILING"
        except Exception:
            pass

        rows_to_int = new_node(nodes, "FunctionNodeFloatToInt")
        rows_to_int.location = (origin_x + 1200, origin_y - 220)
        try:
            rows_to_int.rounding_mode = "CEILING"
        except Exception:
            pass

        branch_area = new_node(nodes, "GeometryNodeAttributeStatistic")
        branch_area.location = (origin_x + 480, origin_y + 80)
        branch_area.data_type = "FLOAT"
        try:
            branch_area.domain = "FACE"
        except Exception:
            pass

        area_ratio = new_node(nodes, "ShaderNodeMath")
        area_ratio.location = (origin_x + 720, origin_y + 120)
        area_ratio.operation = "DIVIDE"

        density_ratio = new_node(nodes, "ShaderNodeMath")
        density_ratio.location = (origin_x + 960, origin_y + 120)
        density_ratio.operation = "SQRT"

        area_columns_float = new_node(nodes, "ShaderNodeMath")
        area_columns_float.location = (origin_x + 1200, origin_y + 120)
        area_columns_float.operation = "MULTIPLY"

        area_rows_float = new_node(nodes, "ShaderNodeMath")
        area_rows_float.location = (origin_x + 1200, origin_y + 20)
        area_rows_float.operation = "MULTIPLY"

        area_min_columns = new_node(nodes, "ShaderNodeMath")
        area_min_columns.location = (origin_x + 1440, origin_y + 120)
        area_min_columns.operation = "MAXIMUM"
        area_min_columns.inputs[1].default_value = 1.0

        area_min_rows = new_node(nodes, "ShaderNodeMath")
        area_min_rows.location = (origin_x + 1440, origin_y + 20)
        area_min_rows.operation = "MAXIMUM"
        area_min_rows.inputs[1].default_value = 1.0

        area_columns_to_int = new_node(nodes, "FunctionNodeFloatToInt")
        area_columns_to_int.location = (origin_x + 1680, origin_y + 120)
        try:
            area_columns_to_int.rounding_mode = "CEILING"
        except Exception:
            pass

        area_rows_to_int = new_node(nodes, "FunctionNodeFloatToInt")
        area_rows_to_int.location = (origin_x + 1680, origin_y + 20)
        try:
            area_rows_to_int.rounding_mode = "CEILING"
        except Exception:
            pass

        uv_unwrap = new_node(nodes, "GeometryNodeUVUnwrap")
        uv_unwrap.location = (origin_x + 240, origin_y)

        columns_plus_one = new_node(nodes, "FunctionNodeIntegerMath")
        columns_plus_one.location = (origin_x + 240, origin_y - 240)
        columns_plus_one.operation = "ADD"
        columns_plus_one.inputs[1].default_value = 1

        rows_plus_one = new_node(nodes, "FunctionNodeIntegerMath")
        rows_plus_one.location = (origin_x + 240, origin_y - 340)
        rows_plus_one.operation = "ADD"
        rows_plus_one.inputs[1].default_value = 1

        mesh_grid = new_node(nodes, "GeometryNodeMeshGrid")
        mesh_grid.location = (origin_x + 480, origin_y - 240)

        grid_translate = new_node(nodes, "ShaderNodeCombineXYZ")
        grid_translate.location = (origin_x + 240, origin_y - 500)
        grid_translate.inputs["X"].default_value = 0.5
        grid_translate.inputs["Y"].default_value = 0.5

        transform_grid = new_node(nodes, "GeometryNodeTransform")
        transform_grid.location = (origin_x + 720, origin_y - 240)

        mesh_to_points = new_node(nodes, "GeometryNodeMeshToPoints")
        mesh_to_points.location = (origin_x + 960, origin_y - 240)
        try:
            mesh_to_points.mode = "FACES"
        except Exception:
            pass

        position_field = new_node(nodes, "GeometryNodeInputPosition")
        position_field.location = (origin_x + 720, origin_y + 220)

        point_index = new_node(nodes, "GeometryNodeInputIndex")
        point_index.location = (origin_x + 960, origin_y - 620)

        row_index = new_node(nodes, "FunctionNodeIntegerMath")
        row_index.location = (origin_x + 1200, origin_y - 620)
        row_index.operation = "DIVIDE"

        row_parity = new_node(nodes, "FunctionNodeIntegerMath")
        row_parity.location = (origin_x + 1440, origin_y - 620)
        row_parity.operation = "MODULO"
        row_parity.inputs[1].default_value = 2

        uv_half_step = new_node(nodes, "ShaderNodeMath")
        uv_half_step.location = (origin_x + 1200, origin_y - 520)
        uv_half_step.operation = "DIVIDE"
        uv_half_step.inputs[0].default_value = 0.5

        stagger_amount = new_node(nodes, "ShaderNodeMath")
        stagger_amount.location = (origin_x + 1680, origin_y - 620)
        stagger_amount.operation = "MULTIPLY"

        stagger_vector = new_node(nodes, "ShaderNodeCombineXYZ")
        stagger_vector.location = (origin_x + 1920, origin_y - 620)

        sample_uv = new_node(nodes, "ShaderNodeVectorMath")
        sample_uv.location = (origin_x + 2160, origin_y - 620)
        sample_uv.operation = "ADD"

        sample_uv_socket = node_socket(sample_uv, "OUTPUT", "Vector", index=0)
        if swap_uv:
            split_sample_uv = new_node(nodes, "ShaderNodeSeparateXYZ")
            split_sample_uv.location = (origin_x + 2400, origin_y - 620)

            rotated_sample_uv = new_node(nodes, "ShaderNodeCombineXYZ")
            rotated_sample_uv.location = (origin_x + 2640, origin_y - 620)

            link(node_socket(split_sample_uv, "INPUT", "Vector", index=0), sample_uv_socket)
            link(node_socket(rotated_sample_uv, "INPUT", "X", index=0), node_socket(split_sample_uv, "OUTPUT", "Y", index=1))
            link(node_socket(rotated_sample_uv, "INPUT", "Y", index=1), node_socket(split_sample_uv, "OUTPUT", "X", index=0))
            sample_uv_socket = node_socket(rotated_sample_uv, "OUTPUT", "Vector", index=0)

        sample_position = new_node(nodes, "GeometryNodeSampleUVSurface")
        sample_position.location = (origin_x + 1440, origin_y - 40)
        sample_position.data_type = "FLOAT_VECTOR"

        sample_normal = new_node(nodes, "GeometryNodeSampleUVSurface")
        sample_normal.location = (origin_x + 1440, origin_y + 120)
        sample_normal.data_type = "FLOAT_VECTOR"

        mean_normal = new_node(nodes, "GeometryNodeAttributeStatistic")
        mean_normal.location = (origin_x + 1440, origin_y + 280)
        mean_normal.data_type = "FLOAT_VECTOR"
        try:
            mean_normal.domain = "FACE"
        except Exception:
            pass

        world_up = new_node(nodes, "ShaderNodeCombineXYZ")
        world_up.location = (origin_x + 1440, origin_y + 440)
        world_up.inputs["Z"].default_value = 1.0

        normal_normalize = new_node(nodes, "ShaderNodeVectorMath")
        normal_normalize.location = (origin_x + 1680, origin_y + 120)
        normal_normalize.operation = "NORMALIZE"

        tangent = new_node(nodes, "ShaderNodeVectorMath")
        tangent.location = (origin_x + 1680, origin_y + 280)
        tangent.operation = "CROSS_PRODUCT"

        tangent_normalize = new_node(nodes, "ShaderNodeVectorMath")
        tangent_normalize.location = (origin_x + 1920, origin_y + 280)
        tangent_normalize.operation = "NORMALIZE"

        axes_to_rotation = new_node(nodes, "FunctionNodeAxesToRotation")
        axes_to_rotation.location = (origin_x + 2160, origin_y + 200)
        axes_to_rotation.primary_axis = "Z"
        axes_to_rotation.secondary_axis = "X"

        capture_surface_normal = new_node(nodes, "GeometryNodeCaptureAttribute")
        capture_surface_normal.location = (origin_x + 1920, origin_y + 40)
        try:
            capture_surface_normal.domain = "POINT"
        except Exception:
            pass
        if hasattr(capture_surface_normal, "capture_items"):
            capture_surface_normal.capture_items.clear()
            capture_surface_normal.capture_items.new("VECTOR", "Surface Normal")
        elif hasattr(capture_surface_normal, "data_type"):
            capture_surface_normal.data_type = "FLOAT_VECTOR"

        rotation_input = new_node(nodes, "FunctionNodeInputRotation")
        rotation_input.location = (origin_x + 2160, origin_y + 40)

        align_to_normal = new_node(
            nodes,
            "FunctionNodeAlignRotationToVector",
            "FunctionNodeAlignEulerToVector",
        )
        align_to_normal.location = (origin_x + 2400, origin_y + 120)
        align_to_normal.axis = "Z"
        if hasattr(align_to_normal, "pivot_axis"):
            align_to_normal.pivot_axis = "AUTO"
        if hasattr(align_to_normal, "pivot"):
            align_to_normal.pivot = "AUTO"

        valid_points = new_node(nodes, "GeometryNodeSeparateGeometry")
        valid_points.location = (origin_x + 1680, origin_y - 240)
        try:
            valid_points.domain = "POINT"
        except Exception:
            pass

        set_position = new_node(nodes, "GeometryNodeSetPosition")
        set_position.location = (origin_x + 1920, origin_y - 240)

        cube = new_node(nodes, "GeometryNodeMeshCube")
        cube.location = (origin_x + 1680, origin_y + 500)

        cube_scale = new_node(nodes, "ShaderNodeCombineXYZ")
        cube_scale.location = (origin_x + 1680, origin_y + 400)

        cube_translation = new_node(nodes, "ShaderNodeCombineXYZ")
        cube_translation.location = (origin_x + 1920, origin_y + 600)

        transform_cube = new_node(nodes, "GeometryNodeTransform")
        transform_cube.location = (origin_x + 2160, origin_y + 500)

        random_id_xy = new_node(nodes, "FunctionNodeIntegerMath")
        random_id_xy.location = (origin_x + 2160, origin_y - 720)
        random_id_xy.operation = "ADD"
        random_id_xy.inputs[1].default_value = branch_seed_offset

        random_id_z = new_node(nodes, "FunctionNodeIntegerMath")
        random_id_z.location = (origin_x + 2160, origin_y - 820)
        random_id_z.operation = "ADD"
        random_id_z.inputs[1].default_value = branch_seed_offset + 1000

        random_id_rot = new_node(nodes, "FunctionNodeIntegerMath")
        random_id_rot.location = (origin_x + 2160, origin_y - 920)
        random_id_rot.operation = "ADD"
        random_id_rot.inputs[1].default_value = branch_seed_offset + 2000

        random_xy = new_node(nodes, "FunctionNodeRandomValue")
        random_xy.location = (origin_x + 2400, origin_y - 720)
        random_xy.data_type = "FLOAT"

        random_z = new_node(nodes, "FunctionNodeRandomValue")
        random_z.location = (origin_x + 2400, origin_y - 820)
        random_z.data_type = "FLOAT"

        random_rot = new_node(nodes, "FunctionNodeRandomValue")
        random_rot.location = (origin_x + 2400, origin_y - 920)
        random_rot.data_type = "FLOAT"

        subtract_xy = new_node(nodes, "ShaderNodeMath")
        subtract_xy.location = (origin_x + 2640, origin_y - 720)
        subtract_xy.operation = "SUBTRACT"
        subtract_xy.inputs[0].default_value = 1.0

        add_xy = new_node(nodes, "ShaderNodeMath")
        add_xy.location = (origin_x + 2880, origin_y - 720)
        add_xy.operation = "ADD"

        row_overlap_scale = new_node(nodes, "ShaderNodeMath")
        row_overlap_scale.location = (origin_x + 2880, origin_y - 600)
        row_overlap_scale.operation = "ADD"
        row_overlap_scale.inputs[0].default_value = 1.0

        overlap_y_scale = new_node(nodes, "ShaderNodeMath")
        overlap_y_scale.location = (origin_x + 3120, origin_y - 600)
        overlap_y_scale.operation = "MULTIPLY"

        subtract_z = new_node(nodes, "ShaderNodeMath")
        subtract_z.location = (origin_x + 2640, origin_y - 820)
        subtract_z.operation = "SUBTRACT"
        subtract_z.inputs[0].default_value = 1.0

        add_z = new_node(nodes, "ShaderNodeMath")
        add_z.location = (origin_x + 2880, origin_y - 820)
        add_z.operation = "ADD"

        negate_rotation = new_node(nodes, "ShaderNodeMath")
        negate_rotation.location = (origin_x + 2640, origin_y - 920)
        negate_rotation.operation = "MULTIPLY"
        negate_rotation.inputs[1].default_value = -1.0

        instance_scale = new_node(nodes, "ShaderNodeCombineXYZ")
        instance_scale.location = (origin_x + 3360, origin_y - 720)

        twist_rotation = new_node(nodes, "ShaderNodeCombineXYZ")
        twist_rotation.location = (origin_x + 3360, origin_y - 920)

        instance_on_points = new_node(nodes, "GeometryNodeInstanceOnPoints")
        instance_on_points.location = (origin_x + 2160, origin_y - 240)

        scale_instances = new_node(nodes, "GeometryNodeScaleInstances")
        scale_instances.location = (origin_x + 2400, origin_y - 240)

        rotate_instances = new_node(nodes, "GeometryNodeRotateInstances")
        rotate_instances.location = (origin_x + 2640, origin_y - 240)
        if hasattr(rotate_instances, "local_space"):
            rotate_instances.local_space = True

        realize_instances = new_node(nodes, "GeometryNodeRealizeInstances")
        realize_instances.location = (origin_x + 2880, origin_y - 240)

        link(node_socket(bounds, "INPUT", "Geometry", index=0), branch_geometry)
        link(node_socket(bounds_size, "INPUT", "Vector", index=0), node_socket(bounds, "OUTPUT", "Max", index=2))
        link(node_socket(bounds_size, "INPUT", "Vector", index=1), node_socket(bounds, "OUTPUT", "Min", index=1))
        link(node_socket(split_bounds_size, "INPUT", "Vector", index=0), node_socket(bounds_size, "OUTPUT", "Vector", index=0))
        link(one_minus_overlap.inputs[1], node_socket(group_input, "OUTPUT", "Row Overlap"))
        link(row_pitch.inputs[0], node_socket(group_input, "OUTPUT", "Tile Size"))
        link(row_pitch.inputs[1], one_minus_overlap.outputs["Value"])
        link(safe_roof_column_extent.inputs[0], split_roof_bounds_size.outputs[column_extent_socket_name])
        link(safe_roof_row_extent.inputs[0], split_roof_bounds_size.outputs[row_extent_socket_name])
        link(auto_columns_float.inputs[0], split_bounds_size.outputs[column_extent_socket_name])
        link(auto_columns_float.inputs[1], safe_roof_column_extent.outputs["Value"])
        link(auto_rows_float.inputs[0], split_bounds_size.outputs[row_extent_socket_name])
        link(auto_rows_float.inputs[1], safe_roof_row_extent.outputs["Value"])
        link(scaled_columns_float.inputs[0], auto_columns_float.outputs["Value"])
        link(scaled_columns_float.inputs[1], node_socket(group_input, "OUTPUT", "Columns"))
        link(scaled_rows_float.inputs[0], auto_rows_float.outputs["Value"])
        link(scaled_rows_float.inputs[1], node_socket(group_input, "OUTPUT", "Rows"))
        link(min_columns.inputs[0], scaled_columns_float.outputs["Value"])
        link(min_rows.inputs[0], scaled_rows_float.outputs["Value"])
        link(node_socket(columns_to_int, "INPUT", "Float", index=0), min_columns.outputs["Value"])
        link(node_socket(rows_to_int, "INPUT", "Float", index=0), min_rows.outputs["Value"])
        link(node_socket(branch_area, "INPUT", "Geometry", index=0), branch_geometry)
        link(node_socket(branch_area, "INPUT", "Attribute", index=2), node_socket(face_area, "OUTPUT", "Area", index=0))
        link(area_ratio.inputs[0], node_socket(branch_area, "OUTPUT", "Sum", index=2))
        link(area_ratio.inputs[1], safe_roof_area.outputs["Value"])
        link(density_ratio.inputs[0], area_ratio.outputs["Value"])
        link(area_columns_float.inputs[0], node_socket(group_input, "OUTPUT", "Columns"))
        link(area_columns_float.inputs[1], density_ratio.outputs["Value"])
        link(area_rows_float.inputs[0], node_socket(group_input, "OUTPUT", "Rows"))
        link(area_rows_float.inputs[1], density_ratio.outputs["Value"])
        link(area_min_columns.inputs[0], area_columns_float.outputs["Value"])
        link(area_min_rows.inputs[0], area_rows_float.outputs["Value"])
        link(node_socket(area_columns_to_int, "INPUT", "Float", index=0), area_min_columns.outputs["Value"])
        link(node_socket(area_rows_to_int, "INPUT", "Float", index=0), area_min_rows.outputs["Value"])

        link(node_socket(uv_unwrap, "INPUT", "Geometry", index=0), branch_geometry)
        link(node_socket(uv_unwrap, "INPUT", "Selection", index=1), node_socket(bool_true, "OUTPUT", "Boolean", index=0))
        link(node_socket(uv_unwrap, "INPUT", "Seam", index=2), node_socket(bool_false, "OUTPUT", "Boolean", index=0))
        link(node_socket(columns_plus_one, "INPUT", "Value", index=0), node_socket(area_columns_to_int, "OUTPUT", "Integer", index=0))
        link(node_socket(rows_plus_one, "INPUT", "Value", index=0), node_socket(area_rows_to_int, "OUTPUT", "Integer", index=0))

        try:
            node_socket(mesh_grid, "INPUT", "Size X", index=0).default_value = 1.0
            node_socket(mesh_grid, "INPUT", "Size Y", index=1).default_value = 1.0
        except Exception:
            pass

        link(node_socket(mesh_grid, "INPUT", "Vertices X", index=2), node_socket(columns_plus_one, "OUTPUT", "Value", index=0))
        link(node_socket(mesh_grid, "INPUT", "Vertices Y", index=3), node_socket(rows_plus_one, "OUTPUT", "Value", index=0))
        link(node_socket(transform_grid, "INPUT", "Geometry", index=0), node_socket(mesh_grid, "OUTPUT", "Mesh", "Geometry", index=0))
        link(node_socket(transform_grid, "INPUT", "Translation", index=1), node_socket(grid_translate, "OUTPUT", "Vector", index=0))
        link(node_socket(mesh_to_points, "INPUT", "Mesh", "Geometry", index=0), node_socket(transform_grid, "OUTPUT", "Geometry", "Mesh", index=0))

        link(node_socket(row_index, "INPUT", "Value", index=0), node_socket(point_index, "OUTPUT", "Index", index=0))
        link(node_socket(row_index, "INPUT", "Value", index=1), node_socket(area_columns_to_int, "OUTPUT", "Integer", index=0))
        link(node_socket(row_parity, "INPUT", "Value", index=0), node_socket(row_index, "OUTPUT", "Value", index=0))
        link(uv_half_step.inputs[1], node_socket(area_columns_to_int, "OUTPUT", "Integer", index=0))
        link(stagger_amount.inputs[0], node_socket(row_parity, "OUTPUT", "Value", index=0))
        link(stagger_amount.inputs[1], uv_half_step.outputs["Value"])
        link(stagger_vector.inputs["X"], stagger_amount.outputs["Value"])
        link(sample_uv.inputs[0], node_socket(position_field, "OUTPUT", "Position", index=0))
        link(sample_uv.inputs[1], node_socket(stagger_vector, "OUTPUT", "Vector", index=0))

        link(node_socket(sample_position, "INPUT", "Mesh", index=0), branch_geometry)
        link(node_socket(sample_position, "INPUT", "Value", index=1), node_socket(position_field, "OUTPUT", "Position", index=0))
        link(node_socket(sample_position, "INPUT", "Source UV Map", "UV Map", index=2), node_socket(uv_unwrap, "OUTPUT", "UV", index=0))
        link(node_socket(sample_position, "INPUT", "Sample UV", index=3), sample_uv_socket)

        link(node_socket(sample_normal, "INPUT", "Mesh", index=0), branch_geometry)
        link(node_socket(sample_normal, "INPUT", "Value", index=1), node_socket(input_normal, "OUTPUT", "Normal", index=0))
        link(node_socket(sample_normal, "INPUT", "Source UV Map", "UV Map", index=2), node_socket(uv_unwrap, "OUTPUT", "UV", index=0))
        link(node_socket(sample_normal, "INPUT", "Sample UV", index=3), sample_uv_socket)

        link(node_socket(mean_normal, "INPUT", "Geometry", index=0), branch_geometry)
        link(node_socket(mean_normal, "INPUT", "Attribute", index=2), node_socket(input_normal, "OUTPUT", "Normal", index=0))
        link(node_socket(normal_normalize, "INPUT", "Vector", index=0), node_socket(sample_normal, "OUTPUT", "Value", index=0))
        link(node_socket(tangent, "INPUT", "Vector", index=0), node_socket(world_up, "OUTPUT", "Vector", index=0))
        link(node_socket(tangent, "INPUT", "Vector", index=1), node_socket(normal_normalize, "OUTPUT", "Vector", index=0))
        link(node_socket(tangent_normalize, "INPUT", "Vector", index=0), node_socket(tangent, "OUTPUT", "Vector", index=0))
        link(node_socket(axes_to_rotation, "INPUT", "Primary Axis", index=0), node_socket(normal_normalize, "OUTPUT", "Vector", index=0))
        link(node_socket(axes_to_rotation, "INPUT", "Secondary Axis", index=1), node_socket(tangent_normalize, "OUTPUT", "Vector", index=0))
        link(node_socket(align_to_normal, "INPUT", "Rotation", index=0), node_socket(rotation_input, "OUTPUT", "Rotation", index=0))
        link(node_socket(capture_surface_normal, "INPUT", "Geometry", index=0), node_socket(mesh_to_points, "OUTPUT", "Points", "Geometry", index=0))
        link(node_socket(capture_surface_normal, "INPUT", "Value", index=1), node_socket(normal_normalize, "OUTPUT", "Vector", index=0))
        captured_points = node_socket(capture_surface_normal, "OUTPUT", "Geometry", index=0)
        captured_surface_normal = node_socket(capture_surface_normal, "OUTPUT", "Attribute", index=1)
        link(node_socket(align_to_normal, "INPUT", "Vector", index=2), captured_surface_normal)

        link(node_socket(valid_points, "INPUT", "Geometry", index=0), captured_points)
        link(node_socket(valid_points, "INPUT", "Selection", index=1), node_socket(sample_position, "OUTPUT", "Is Valid", index=1))
        link(node_socket(set_position, "INPUT", "Geometry", index=0), node_socket(valid_points, "OUTPUT", "Selection", index=0))
        link(node_socket(set_position, "INPUT", "Position", index=2), node_socket(sample_position, "OUTPUT", "Value", index=0))

        try:
            node_socket(cube, "INPUT", "Size").default_value = 1.0
        except Exception:
            pass

        link(node_socket(cube_scale, "INPUT", "X", index=0), node_socket(group_input, "OUTPUT", "Tile Size"))
        link(node_socket(cube_scale, "INPUT", "Y", index=1), node_socket(group_input, "OUTPUT", "Tile Size"))
        link(node_socket(cube_scale, "INPUT", "Z", index=2), node_socket(group_input, "OUTPUT", "Thickness"))
        link(node_socket(cube_translation, "INPUT", "Z", index=2), node_socket(group_input, "OUTPUT", "Surface Offset"))
        link(node_socket(transform_cube, "INPUT", "Geometry", index=0), node_socket(cube, "OUTPUT", "Mesh", "Geometry", index=0))
        link(node_socket(transform_cube, "INPUT", "Translation", index=1), node_socket(cube_translation, "OUTPUT", "Vector", index=0))
        link(node_socket(transform_cube, "INPUT", "Scale", index=3), node_socket(cube_scale, "OUTPUT", "Vector", index=0))

        link(node_socket(instance_on_points, "INPUT", "Points", "Geometry", index=0), node_socket(set_position, "OUTPUT", "Geometry", index=0))
        link(node_socket(instance_on_points, "INPUT", "Instance", index=2), node_socket(transform_cube, "OUTPUT", "Geometry", index=0))
        try:
            link(node_socket(instance_on_points, "INPUT", "Rotation"), node_socket(align_to_normal, "OUTPUT", "Rotation", index=0))
        except Exception:
            link(node_socket(instance_on_points, "INPUT", "Rotation", index=5), node_socket(align_to_normal, "OUTPUT", "Rotation", index=0))

        random_xy.inputs["Min"].default_value = 0.0
        random_xy.inputs["Max"].default_value = 1.0
        random_z.inputs["Min"].default_value = 0.0
        random_z.inputs["Max"].default_value = 1.0
        link(node_socket(random_id_xy, "INPUT", "Value", index=0), node_socket(group_input, "OUTPUT", "Seed"))
        link(node_socket(random_id_z, "INPUT", "Value", index=0), node_socket(group_input, "OUTPUT", "Seed"))
        link(node_socket(random_id_rot, "INPUT", "Value", index=0), node_socket(group_input, "OUTPUT", "Seed"))
        link(node_socket(random_id_xy, "INPUT", "Value", index=1), node_socket(point_index, "OUTPUT", "Index", index=0))
        link(node_socket(random_id_z, "INPUT", "Value", index=1), node_socket(point_index, "OUTPUT", "Index", index=0))
        link(node_socket(random_id_rot, "INPUT", "Value", index=1), node_socket(point_index, "OUTPUT", "Index", index=0))
        try:
            link(node_socket(random_xy, "INPUT", "ID", "Seed", index=7), node_socket(random_id_xy, "OUTPUT", "Value", index=0))
            link(node_socket(random_z, "INPUT", "ID", "Seed", index=7), node_socket(random_id_z, "OUTPUT", "Value", index=0))
            link(node_socket(random_rot, "INPUT", "ID", "Seed", index=7), node_socket(random_id_rot, "OUTPUT", "Value", index=0))
        except Exception:
            pass

        link(subtract_xy.inputs[1], node_socket(group_input, "OUTPUT", "Scale Jitter"))
        link(add_xy.inputs[0], subtract_xy.outputs["Value"])
        link(add_xy.inputs[1], random_xy.outputs["Value"])
        link(row_overlap_scale.inputs[1], node_socket(group_input, "OUTPUT", "Row Overlap"))
        link(overlap_y_scale.inputs[0], add_xy.outputs["Value"])
        link(overlap_y_scale.inputs[1], row_overlap_scale.outputs["Value"])
        link(subtract_z.inputs[1], node_socket(group_input, "OUTPUT", "Thickness Jitter"))
        link(add_z.inputs[0], subtract_z.outputs["Value"])
        link(add_z.inputs[1], random_z.outputs["Value"])
        link(node_socket(negate_rotation, "INPUT", "Value", index=0), node_socket(group_input, "OUTPUT", "Rotation Jitter"))
        link(node_socket(random_rot, "INPUT", "Min", index=2), node_socket(negate_rotation, "OUTPUT", "Value", index=0))
        link(node_socket(random_rot, "INPUT", "Max", index=3), node_socket(group_input, "OUTPUT", "Rotation Jitter"))
        link(instance_scale.inputs["X"], add_xy.outputs["Value"])
        link(instance_scale.inputs["Y"], overlap_y_scale.outputs["Value"])
        link(instance_scale.inputs["Z"], add_z.outputs["Value"])
        link(twist_rotation.inputs["Z"], random_rot.outputs["Value"])

        link(node_socket(scale_instances, "INPUT", "Instances", "Geometry", index=0), node_socket(instance_on_points, "OUTPUT", "Instances", "Geometry", index=0))
        link(node_socket(scale_instances, "INPUT", "Scale", index=2), node_socket(instance_scale, "OUTPUT", "Vector", index=0))
        link(node_socket(rotate_instances, "INPUT", "Instances", "Geometry", index=0), node_socket(scale_instances, "OUTPUT", "Instances", "Geometry", index=0))
        try:
            link(node_socket(rotate_instances, "INPUT", "Rotation", index=3), node_socket(twist_rotation, "OUTPUT", "Vector", index=0))
        except Exception:
            pass
        link(node_socket(realize_instances, "INPUT", "Geometry", index=0), node_socket(rotate_instances, "OUTPUT", "Instances", "Geometry", index=0))
        return node_socket(realize_instances, "OUTPUT", "Geometry", index=0)

    branch_outputs = [
        build_branch(node_socket(xp_split, "OUTPUT", "Selection", index=0), -1460, -700, 0),
        build_branch(node_socket(xp_split, "OUTPUT", "Inverted", index=1), -1460, 450, 3000, swap_uv=True),
        build_branch(node_socket(xn_split, "OUTPUT", "Selection", index=0), -1460, 1600, 6000, swap_uv=True),
        build_branch(node_socket(xn_split, "OUTPUT", "Inverted", index=1), -1460, 2750, 9000),
    ]

    join_chain = node_socket(group_input, "OUTPUT", "Geometry", index=0)
    for index, branch_output in enumerate(branch_outputs):
        join_node = new_node(nodes, "GeometryNodeJoinGeometry")
        join_node.location = (3500 + index * 180, -120)
        link(node_socket(join_node, "INPUT", "Geometry", index=0), join_chain)
        link(node_socket(join_node, "INPUT", "Geometry", index=1), branch_output)
        join_chain = node_socket(join_node, "OUTPUT", "Geometry", index=0)

    link(node_socket(group_output, "INPUT", "Geometry", index=0), join_chain)
    node_group["cd_shingle_group_version"] = shingle_group_version

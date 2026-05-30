# Blender MCP Snippets

Use these with `scripts/blender_mcp_exec.py` or an equivalent null-byte-delimited JSON socket client.

## Scene Summary

```python
import bpy
result = {
    "scene": bpy.context.scene.name if bpy.context.scene else None,
    "objects": sorted(obj.name for obj in bpy.data.objects),
    "node_groups": sorted(group.name for group in bpy.data.node_groups),
    "materials": sorted(mat.name for mat in bpy.data.materials),
}
```

## Probe Node Sockets

```python
import bpy
tree = bpy.data.node_groups.new("MCP_SOCKET_PROBE", "GeometryNodeTree")
node = tree.nodes.new("GeometryNodeCaptureAttribute")
if hasattr(node, "capture_items"):
    node.capture_items.clear()
    node.capture_items.new("VECTOR", "Surface Normal")
result = {
    "node": node.bl_idname,
    "inputs": [(s.name, s.identifier, s.bl_idname) for s in node.inputs],
    "outputs": [(s.name, s.identifier, s.bl_idname) for s in node.outputs],
}
bpy.data.node_groups.remove(tree)
```

## Reversible Write Test

```python
import bpy
name = "MCP_Temp_Write_Test"
if name in bpy.data.objects:
    bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
bpy.ops.mesh.primitive_cube_add(size=0.25, location=(1.5, 0, 0.125))
obj = bpy.context.object
obj.name = name
created = obj.name
bpy.data.objects.remove(obj, do_unlink=True)
result = {"created_then_deleted": created, "still_exists": name in bpy.data.objects}
```

# Official Blender Docs Reference

Use this file when a task needs official Blender documentation.

## Primary Sources

- Blender Manual latest: https://docs.blender.org/manual/en/latest/
- Blender Manual 5.1: https://docs.blender.org/manual/en/5.1/
- Blender Python API current: https://docs.blender.org/api/current/
- Blender Lab MCP Server: https://www.blender.org/lab/mcp-server/

Prefer version-specific manual paths when the user names a version. Use `latest` only when the user asks for current behavior or the active Blender version matches latest.

## Geometry Nodes Pages Often Needed

- Geometry Nodes overview: `/manual/en/latest/modeling/geometry_nodes/`
- Capture Attribute: `/manual/en/latest/modeling/geometry_nodes/attribute/capture_attribute.html`
- Attribute Statistic: `/manual/en/latest/modeling/geometry_nodes/attribute/attribute_statistic.html`
- Face Area: `/manual/en/latest/modeling/geometry_nodes/mesh/read/face_area.html`
- Sample UV Surface: `/manual/en/latest/modeling/geometry_nodes/mesh/sample/sample_uv_surface.html`
- Instance on Points: `/manual/en/latest/modeling/geometry_nodes/instances/instance_on_points.html`
- Scale Instances: `/manual/en/latest/modeling/geometry_nodes/instances/scale_instances.html`
- Rotate Instances: `/manual/en/latest/modeling/geometry_nodes/instances/rotate_instances.html`
- Realize Instances: `/manual/en/latest/modeling/geometry_nodes/instances/realize_instances.html`
- Axes to Rotation: `/manual/en/latest/modeling/geometry_nodes/utilities/rotation/axes_to_rotation.html`
- Split To Instances: `/manual/en/latest/modeling/geometry_nodes/geometry/operations/split_to_instances.html`

## Search Patterns

Use targeted searches:

```text
site:docs.blender.org/manual/en/latest/modeling/geometry_nodes <node name>
site:docs.blender.org/api/current bpy.types.<TypeName>
site:docs.blender.org/api/current <property or class>
```

When browsing is unavailable, use live Blender introspection for exact API/socket details and clearly label it as live introspection rather than documentation.

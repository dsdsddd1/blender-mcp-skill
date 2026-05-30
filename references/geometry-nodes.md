# Geometry Nodes Notes

Use this file for implementation-sensitive Geometry Nodes work.

## Implementation Rules

- Verify sockets in Blender before wiring nodes through Python.
- Use `node.inputs`/`node.outputs` names and identifiers from the active Blender version.
- Avoid assuming old dynamic socket APIs still exist.
- Remember that fields are lazy and can be reevaluated after geometry changes.
- Capture sampled values before `Set Position`, `Realize Instances`, domain changes, or geometry joins if later nodes need the old field meaning.

## Blender 5.1 Capture Attribute

In the tested Blender 5.1 environment, `GeometryNodeCaptureAttribute` exposes `capture_items`, not a simple `data_type` property.

Pattern:

```python
capture = nodes.new("GeometryNodeCaptureAttribute")
capture.domain = "POINT"
capture.capture_items.clear()
capture.capture_items.new("VECTOR", "Surface Normal")
```

The dynamic sockets then include:

```text
inputs:  Geometry, Surface Normal, virtual
outputs: Geometry, Surface Normal, virtual
```

Use the named vector output as the captured field.

## Regular Tiles vs Scatter

Random surface scatter:

```text
Distribute Points on Faces
-> Instance on Points
```

Regular shingles/tiles:

```text
local grid or UV grid
-> Sample UV Surface position
-> Sample/Capture normal before moving points
-> Set Position
-> Instance on Points with captured normal rotation
```

For multi-face shingles, avoid one global UV/grid across multiple roof faces. Prefer face/island-local branches.

## Known Shingle Lessons

- If only a few shingles align to a slope, check whether `Position` was used as UV after `Set Position`.
- If changing density leaves one or two tiles, inspect whether auto row/column math collapsed to `1 x 1`.
- Area-ratio scaling is more robust than world-axis bounding-box scaling for sloped/triangular roof faces:

```text
scale = sqrt(branch_area / total_roof_area)
branch_columns = total_columns * scale
branch_rows = total_rows * scale
```

Compute area with:

```text
Mesh Face Area
-> Attribute Statistic on FACE domain
-> Sum
```

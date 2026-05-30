# Wood Shingles HTTP Bridge Example / 木瓦 HTTP 桥接示例

## English

This example is a Blender add-on that exposes a tiny local HTTP bridge for driving Geometry Nodes from an external script.

It demonstrates:

- A non-blocking socket server inside Blender.
- Polling with `bpy.app.timers` so Blender's main thread owns all `bpy` changes.
- Minimal HTTP endpoints for scene inspection and Geometry Nodes modifier updates.
- A procedural wood-shingles node group built and hot-reloaded from Python.
- A debug-friendly workflow for rebuilding a Geometry Nodes group without reinstalling the add-on.

The example is intentionally small and local-only. It is not an authentication or production networking template.

### Files

- `blender_collection_deformer/__init__.py`: Blender add-on and local HTTP bridge.
- `blender_collection_deformer/dev_override.py`: Hot-reload Geometry Nodes builder for the wood-shingles setup.
- `client_example.py`: Minimal Python client for the collection-deformer endpoint.

### Default Server

```text
http://127.0.0.1:8765
```

Useful endpoints:

```text
GET  /health
GET  /v1/scene
POST /v1/collection-deformer
POST /v1/wood-shingles
GET  /v1/dev/status
POST /v1/dev/rebuild-wood-shingles
```

### Example Wood-Shingles Request

```powershell
$body = @{
  target_object = 'Plane'
  columns = 36
  rows = 36
  tile_size = 0.11
  thickness = 0.022
  scale_jitter = 0.02
  thickness_jitter = 0.04
  rotation_jitter_degrees = 0.0
  surface_offset = 0.003
  row_overlap = 0.12
  seed = 10
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri http://127.0.0.1:8765/v1/wood-shingles `
  -Method Post `
  -ContentType 'application/json' `
  -Body $body
```

### Geometry Nodes Lessons Demonstrated

- Capture sampled surface normals before `Set Position` changes the point positions.
- Avoid using a field whose meaning changes after geometry operations.
- Use face-area ratios to keep regular tile density more consistent across uneven faces.
- Keep instances live until transforms and randomization are complete.

## 中文

这个示例是一个 Blender 插件：它在 Blender 内部启动一个很小的本地 HTTP 桥接服务，让外部脚本可以驱动 Geometry Nodes。

它演示了：

- 在 Blender 内部使用非阻塞 socket。
- 用 `bpy.app.timers` 轮询，确保所有 `bpy` 修改仍然发生在 Blender 主线程。
- 用少量 HTTP endpoint 检查场景、更新 Geometry Nodes modifier。
- 通过 Python 构建并热重载一个程序化木瓦节点组。
- 不反复重装插件，也能调试和重建 Geometry Nodes 的工作流。

这个示例只面向本地实验，不是生产网络服务或认证系统模板。

### 文件说明

- `blender_collection_deformer/__init__.py`：Blender 插件和本地 HTTP 桥接服务。
- `blender_collection_deformer/dev_override.py`：木瓦 Geometry Nodes 的热重载构建脚本。
- `client_example.py`：调用 collection-deformer endpoint 的最小 Python 客户端。

### 默认服务地址

```text
http://127.0.0.1:8765
```

常用接口：

```text
GET  /health
GET  /v1/scene
POST /v1/collection-deformer
POST /v1/wood-shingles
GET  /v1/dev/status
POST /v1/dev/rebuild-wood-shingles
```

### 木瓦请求示例

```powershell
$body = @{
  target_object = 'Plane'
  columns = 36
  rows = 36
  tile_size = 0.11
  thickness = 0.022
  scale_jitter = 0.02
  thickness_jitter = 0.04
  rotation_jitter_degrees = 0.0
  surface_offset = 0.003
  row_overlap = 0.12
  seed = 10
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri http://127.0.0.1:8765/v1/wood-shingles `
  -Method Post `
  -ContentType 'application/json' `
  -Body $body
```

### 这个示例体现的 Geometry Nodes 经验

- 在 `Set Position` 改变点位置之前，先捕获采样到的表面法线。
- 不要在几何操作之后继续依赖含义已经变化的字段。
- 用面面积比例来让不同大小面的规则 tile 密度更一致。
- 在完成变换和随机化之前，尽量保持实例状态。

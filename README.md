<p align="center">
  <img src="assets/readme-banner.svg" alt="Blender MCP Skill banner" width="100%">
</p>

<h1 align="center">Blender MCP Skill</h1>

<p align="center">
  <strong>A Codex skill for Blender work that starts from official docs, verifies through MCP, and ships practical Geometry Nodes workflows.</strong>
</p>

<p align="center">
  <a href="https://www.blender.org/lab/mcp-server/"><img alt="Blender MCP" src="https://img.shields.io/badge/Blender-MCP-ff7a1a?style=for-the-badge"></a>
  <a href="https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/"><img alt="Geometry Nodes" src="https://img.shields.io/badge/Geometry%20Nodes-docs--first-4c8eda?style=for-the-badge"></a>
  <img alt="Codex Skill" src="https://img.shields.io/badge/Codex-Skill-111827?style=for-the-badge">
  <img alt="Example Included" src="https://img.shields.io/badge/Example-HTTP%20Bridge-22c55e?style=for-the-badge">
</p>

---

`blender-manual` helps Codex answer, build, and debug Blender tasks with better version accuracy. It is designed for Blender Manual/API questions, Geometry Nodes implementation, node socket verification, Blender MCP workflows, and add-on debugging.

The guiding rule is simple: use official documentation first, inspect the live Blender scene when precision matters, and only then make implementation decisions.

## What It Helps With

- Reading Blender Manual and Python API pages before making claims.
- Checking exact node `bl_idname`, socket names, identifiers, and domains.
- Querying the active Blender session through the official MCP server on `localhost:9876`.
- Inspecting scenes, objects, materials, modifiers, and node trees.
- Building and debugging generated Geometry Nodes node groups.
- Keeping reusable Blender snippets close to the skill instead of scattered across chats.

## Repository Map

| Path | Purpose |
| --- | --- |
| `SKILL.md` | Main skill instructions and operating workflow. |
| `agents/openai.yaml` | Codex UI metadata. |
| `references/official-docs.md` | Official documentation links and search patterns. |
| `references/geometry-nodes.md` | Geometry Nodes implementation notes. |
| `references/mcp-snippets.md` | Reusable Blender MCP Python snippets. |
| `scripts/blender_mcp_exec.py` | Execute Python in Blender through the official MCP socket. |
| `scripts/fetch_blender_doc.py` | Fetch and summarize official Blender documentation pages. |
| `examples/wood-shingles-http-bridge/` | Example add-on showing a local HTTP bridge driving a procedural Geometry Nodes setup. |

## Quick Start

Fetch an official Blender documentation page:

```powershell
python scripts/fetch_blender_doc.py "https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/attribute/capture_attribute.html"
```

Query the active Blender scene through MCP:

```powershell
python scripts/blender_mcp_exec.py --code "import bpy; result={'objects': sorted(obj.name for obj in bpy.data.objects)}"
```

Inspect the included bridge example:

```text
examples/wood-shingles-http-bridge/
```

## Included Example

The `wood-shingles-http-bridge` example is a small Blender add-on that exposes a local HTTP bridge and rebuilds a procedural Geometry Nodes setup from Python. It demonstrates:

- Running a tiny local server inside Blender without blocking the UI.
- Applying scene changes safely through Blender's main thread.
- Rebuilding a Geometry Nodes group from script during iteration.
- Capturing sampled surface normals before instancing, so tiles follow roof slope.
- Scaling layout density by face area, so small and large roof faces keep consistent spacing.

Read more in [`examples/wood-shingles-http-bridge/README.md`](examples/wood-shingles-http-bridge/README.md).

## Evidence Order

1. Official Blender documentation from `docs.blender.org`.
2. Live Blender introspection through the official MCP socket.
3. Local project evidence such as add-ons, scripts, generated node groups, and scene state.

## Security Note

The official Blender MCP server can execute generated Python code inside Blender. Use it carefully, especially with important `.blend` files or systems containing sensitive data.

---

## 中文说明

`blender-manual` 是一个给 Codex 使用的 Blender Skill，用来把 Blender 官方文档、官方 MCP Server 和当前 Blender 场景检查结合起来。它适合处理 Blender Manual、Python API、Geometry Nodes、节点 socket 名称确认、插件调试和程序化节点组生成。

它的工作方式是：先查官方文档，需要精确时再通过 MCP 读取当前 Blender，最后结合本地项目里的脚本、插件和节点组来判断。

## 适合做什么

- 查询 Blender Manual 和 Python API。
- 确认 Geometry Nodes 节点的 `bl_idname`、socket 名称、identifier 和 domain。
- 通过官方 MCP Server，也就是 `localhost:9876`，读取当前 Blender 会话。
- 检查场景中的对象、材质、modifier 和 node group。
- 构建、调试由脚本生成的 Geometry Nodes。
- 把常用 Blender MCP 片段整理成可复用资料。

## 文件结构

| 路径 | 作用 |
| --- | --- |
| `SKILL.md` | Skill 的触发说明和工作流程。 |
| `agents/openai.yaml` | Codex UI 元数据。 |
| `references/official-docs.md` | 官方文档链接和搜索方式。 |
| `references/geometry-nodes.md` | Geometry Nodes 实现注意事项。 |
| `references/mcp-snippets.md` | 常用 Blender MCP Python 片段。 |
| `scripts/blender_mcp_exec.py` | 通过官方 MCP socket 在 Blender 里执行 Python。 |
| `scripts/fetch_blender_doc.py` | 抓取并摘要 Blender 官方文档页面。 |
| `examples/wood-shingles-http-bridge/` | 一个本地 HTTP 桥接插件示例，用来驱动程序化 Geometry Nodes。 |

## 示例

抓取 Blender 官方文档页面：

```powershell
python scripts/fetch_blender_doc.py "https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/attribute/capture_attribute.html"
```

通过 MCP 查询当前 Blender 场景：

```powershell
python scripts/blender_mcp_exec.py --code "import bpy; result={'objects': sorted(obj.name for obj in bpy.data.objects)}"
```

查看我们做的桥接插件示例：

```text
examples/wood-shingles-http-bridge/
```

## 示例亮点

`wood-shingles-http-bridge` 是一个小型 Blender add-on 示例，展示如何从外部脚本通过本地 HTTP bridge 驱动 Blender，并用 Python 重建 Geometry Nodes。它记录了这次木瓦项目里真正解决问题的几个关键点：

- 在 Blender 内部运行非阻塞本地服务。
- 用 Blender 主线程安全地修改场景。
- 热重载 Geometry Nodes 构建脚本。
- 先捕获采样表面法线，再用于实例旋转，让瓦片贴合屋顶斜度。
- 按面面积缩放行列密度，让大小不同的屋顶面保持一致间距。

更多说明见 [`examples/wood-shingles-http-bridge/README.md`](examples/wood-shingles-http-bridge/README.md)。

## 安全提醒

官方 Blender MCP Server 可以在 Blender 内执行生成的 Python 代码。处理重要 `.blend` 文件或含敏感数据的系统时，请谨慎使用。

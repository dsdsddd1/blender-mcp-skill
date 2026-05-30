# Blender Manual Skill / Blender 使用手册 Skill

## English

`blender-manual` is a Codex skill for working with Blender using official documentation and live Blender introspection.

It helps Codex answer and implement Blender tasks with better version accuracy, especially for:

- Blender Manual and Python API questions.
- Geometry Nodes behavior and node graph implementation.
- Exact node `bl_idname`, socket names, identifiers, and domains.
- Official Blender MCP server usage through `localhost:9876`.
- Scene, object, material, modifier, and node-tree inspection.
- Debugging Blender add-ons or generated Geometry Nodes setups.

The skill prefers three evidence levels:

1. Official Blender documentation from `docs.blender.org`.
2. Live Blender introspection through the official MCP socket.
3. Local project evidence such as add-ons, scripts, and generated node groups.

### Included Files

- `SKILL.md`: Main trigger description and operating workflow.
- `agents/openai.yaml`: Codex UI metadata.
- `references/official-docs.md`: Official documentation links and search patterns.
- `references/geometry-nodes.md`: Geometry Nodes implementation notes.
- `references/mcp-snippets.md`: Reusable Blender MCP Python snippets.
- `scripts/blender_mcp_exec.py`: Execute Python in Blender through the official MCP socket.
- `scripts/fetch_blender_doc.py`: Fetch and summarize official Blender documentation pages.

### Example Usage

Fetch a Blender documentation page:

```powershell
python scripts/fetch_blender_doc.py "https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/attribute/capture_attribute.html"
```

Query the active Blender scene through MCP:

```powershell
python scripts/blender_mcp_exec.py --code "import bpy; result={'objects': sorted(obj.name for obj in bpy.data.objects)}"
```

### Security Note

The official Blender MCP server can execute generated Python code inside Blender. Use it carefully, especially with important `.blend` files or systems containing sensitive data.

## 中文

`blender-manual` 是一个给 Codex 使用的 Blender Skill，用来结合 Blender 官方文档和当前 Blender 会话的实时 introspection 来回答、实现和调试 Blender 任务。

它特别适合：

- 查询 Blender Manual 和 Python API。
- 理解和实现 Geometry Nodes 节点图。
- 确认节点的 `bl_idname`、socket 名称、identifier 和 domain。
- 使用官方 Blender MCP Server，也就是 `localhost:9876`。
- 检查当前场景里的对象、材质、modifier、node group。
- 调试 Blender add-on 或脚本生成的 Geometry Nodes。

这个 skill 的判断优先级是：

1. 优先查 `docs.blender.org` 官方文档。
2. 需要精确节点/socket/API 信息时，通过官方 MCP 读取当前 Blender。
3. 再结合本地项目里的 add-on、脚本和生成节点组。

### 文件说明

- `SKILL.md`：skill 的触发描述和工作流程。
- `agents/openai.yaml`：Codex UI 元数据。
- `references/official-docs.md`：官方文档链接和搜索方式。
- `references/geometry-nodes.md`：Geometry Nodes 实现注意事项。
- `references/mcp-snippets.md`：常用 Blender MCP Python 片段。
- `scripts/blender_mcp_exec.py`：通过官方 MCP socket 在 Blender 里执行 Python。
- `scripts/fetch_blender_doc.py`：抓取并摘要 Blender 官方文档页面。

### 使用示例

抓取 Blender 官方文档页面：

```powershell
python scripts/fetch_blender_doc.py "https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/attribute/capture_attribute.html"
```

通过 MCP 查询当前 Blender 场景：

```powershell
python scripts/blender_mcp_exec.py --code "import bpy; result={'objects': sorted(obj.name for obj in bpy.data.objects)}"
```

### 安全提醒

官方 Blender MCP Server 可以在 Blender 内执行生成的 Python 代码。处理重要 `.blend` 文件或含敏感数据的系统时要谨慎使用。

---
name: blender-manual
description: Use when Codex needs authoritative Blender help, especially Blender Manual/API questions, Geometry Nodes behavior, node socket names, Blender MCP server usage, scene inspection, modifier/node-tree analysis, or implementation guidance that must match the active Blender version. Prefer official Blender documentation and live Blender introspection over memory; use this for building, debugging, or documenting Blender Python, Geometry Nodes, materials, modifiers, and add-ons.
---

# Blender Manual

## Core Rule

Prefer current official Blender sources and live Blender introspection over recalled knowledge. Blender node names, socket names, and Python APIs change between versions.

Use three evidence levels:

1. **Official docs**: `docs.blender.org` manual/API pages for stable explanation and user-facing behavior.
2. **Live Blender introspection**: active Blender session through the official MCP socket when exact node/socket/API details matter.
3. **Local project evidence**: existing add-ons, node builder scripts, and generated node groups in the workspace.

State which level was used when the answer depends on it.

## Quick Workflow

1. Identify Blender version from the user, current file, or live session.
2. For changing/current docs, browse official Blender domains or fetch the official docs page.
3. For Geometry Nodes implementation, inspect the live node type/socket names in Blender before writing code.
4. For project add-ons, read local files before changing behavior.
5. Validate by running a minimal Blender MCP query or rebuilding the node group when possible.

## Official Documentation

Use official sources first:

- Manual latest: `https://docs.blender.org/manual/en/latest/`
- Python API current: `https://docs.blender.org/api/current/`
- Blender Lab MCP page: `https://www.blender.org/lab/mcp-server/`
- Blender source/projects when architecture details matter: `https://projects.blender.org/`

When the user asks for "latest", "official", or version-sensitive behavior, browse instead of relying on memory.

For deeper page and search patterns, read [references/official-docs.md](references/official-docs.md).

## Blender MCP Socket

If the official Blender MCP add-on is running, it normally listens at:

```text
localhost:9876
```

Protocol:

```json
{"type":"execute","code":"result = {\"ok\": True}","strict_json":true}\0
```

The code runs inside Blender and must set `result` to a JSON-serializable dict.

Use the bundled script when available:

```powershell
python scripts/blender_mcp_exec.py --code "result={'ok': True}"
```

Use MCP for:

- Scene/object/material/node-group inspection.
- Exact node socket names and identifiers.
- Safe, reversible tests such as creating then deleting a temporary object.
- Reading current modifiers and node trees.

Avoid destructive code unless the user explicitly requests it. The official MCP page warns that generated code can remove or exfiltrate data. Treat it as powerful and unsafe by default.

For reusable snippets, read [references/mcp-snippets.md](references/mcp-snippets.md).

## Geometry Nodes

For Geometry Nodes tasks:

- Verify node `bl_idname` and sockets in the active Blender version.
- Prefer fields and domains deliberately; many bugs come from fields being reevaluated after geometry changes.
- Capture values before operations that change the domain or meaning of fields.
- Use `Capture Attribute` with Blender 5.1's `capture_items` API when dynamic capture sockets are required.
- For scattering, distinguish random surface scatter from regular layout:
  - Pebbles/grass: `Distribute Points on Faces -> Instance on Points`.
  - Regular tiles/panels: local grid/UV sampling, captured normals, row/column control.

For node-specific notes, read [references/geometry-nodes.md](references/geometry-nodes.md).

## Answer Style

When explaining Blender behavior:

- Separate "manual says" from "live Blender reports".
- Include exact page links when documentation was consulted.
- Include exact `bl_idname`, socket names, and domains when implementing nodes.
- Mention version assumptions explicitly.
- If a suggested node graph is untested, say so.

## Validation

Before calling a Geometry Nodes fix complete, prefer one of:

- Rebuild the node group successfully in Blender.
- Query the created node/socket layout through MCP.
- Run a reversible scene test.
- Ask the user for a screenshot only after automated checks pass.

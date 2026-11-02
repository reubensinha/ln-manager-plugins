# MCPServer plugin

Exposes the LN-Manager library to AI tools over the [Model Context Protocol](https://modelcontextprotocol.io) using the Streamable HTTP transport. The endpoint is served by the main app on the same port, under this plugin's API prefix:

```text
http://<host>:9583/api/plugins/MCPServer/mcp        (Docker / production)
http://localhost:8000/api/plugins/MCPServer/mcp     (fastapi dev)
```

Read-only. No authentication — same trust model as the rest of the app (keep it behind your LAN / reverse proxy). `GET /api/plugins/MCPServer/info` reports the endpoint and the tool list.

## Tools

| Tool | Purpose |
| --- | --- |
| `list_collections()` | Collections in the library |
| `list_library()` | Every series group with volume count, last/next release date, languages |
| `get_series_group(group_id)` | A group and the series (editions/languages) in it |
| `get_series(series_id)` | Full series metadata plus its books |
| `get_book(book_id)` | A book and its releases |
| `search_library(query)` | Case-insensitive match on title / romaji / original title / aliases |
| `upcoming_releases(days=30)` | Releases dated within the next N days, with book and series titles |

## Connecting a client

Claude Code:

```bash
claude mcp add --transport http ln-manager http://localhost:9583/api/plugins/MCPServer/mcp
```

Claude Desktop / other clients: add a remote MCP server of type "Streamable HTTP" with the URL above.

## Disabling

Toggle the plugin off on the Settings → Plugins page and restart the backend; the endpoint then falls through to the normal SPA handler.

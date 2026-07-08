# odoo-mcp-server

Secure Model Context Protocol (MCP) server for Odoo JSON-RPC.

The server exposes typed MCP tools for common Odoo operations and guarded mutation tools for controlled administration. It is intentionally safe by default in one simple way: read-only mode is enabled unless you opt in to mutations. Model and method allowlists default to `*` so local/admin workflows do not need extra configuration unless you want to tighten them.

## Current status and limits

This project is useful for MCP-driven Odoo exploration and guarded automation, but it is not a blanket “complete Odoo API” proxy by default. Dangerous operations are disabled unless explicitly enabled and confirmed.

Implemented guardrails:

- `ODOO_READ_ONLY=true` by default; `READ_ONLY=true` is also accepted.
- Model allowlist via `ODOO_ALLOWED_MODELS` / `ALLOWED_MODELS` (glob patterns supported, default `*`).
- Method allowlist for `call_method` via `ODOO_ALLOWED_METHODS` / `ALLOWED_METHODS` (default `*`).
- No tools are disabled by default beyond read-only hiding/blocking mutation tools while `ODOO_READ_ONLY=true`.
- Mutating tools require `confirm=true` in the payload.
- Audit logs for mutations: user, tool, model, method, ids, approximate diff hash/fields.
- Model-name, method-name, domain, ids, limit, and sensitive-field validation.
- `search_read` requires an explicit `limit`; max limit defaults to 500.
- Secrets are redacted from structured logs.
- Synchronous Odoo RPC is run through `asyncio.to_thread` from async MCP handlers to avoid blocking the MCP event loop.

Known limits:

- The Odoo client still uses sync `httpx.Client`; a future version should migrate fully to `httpx.AsyncClient`.
- The local TTL cache is intentionally small and simple; it is not a distributed or bounded production cache.
- Allowlist defaults are permissive (`*` models and `*` methods) so existing workflows continue to work; tighten them for production.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Run the server:

```bash
odoo-mcp-server
# or
python -m odoo_mcp.mcp_server
```

## Claude Desktop / MCP configuration

```json
{
  "mcpServers": {
    "odoo": {
      "command": "/absolute/path/to/odoo-mcp/.venv/bin/odoo-mcp-server",
      "env": {
        "ODOO_URL": "https://your-instance.odoo.com",
        "ODOO_DB": "your_database",
        "ODOO_USERNAME": "your_username",
        "ODOO_PASSWORD": "your_password",
        "ODOO_READ_ONLY": "true",
        "ODOO_ALLOWED_MODELS": "res.partner,sale.order,account.move,product.*"
      }
    }
  }
}
```

## Security configuration

| Variable | Default | Description |
| --- | --- | --- |
| `ODOO_READ_ONLY` / `READ_ONLY` | `true` | Blocks create/write/copy/unlink/load/call_method when true. |
| `ODOO_ALLOWED_MODELS` / `ALLOWED_MODELS` | `*` | Comma-separated allowlist; glob patterns are accepted. |
| `ODOO_ALLOWED_METHODS` / `ALLOWED_METHODS` | `*` | Comma-separated methods permitted for `call_method` when read-only is disabled. |
| `ODOO_DISABLED_TOOLS` / `DISABLED_TOOLS` | empty | Optional tools to hide and block by policy. |
| `ODOO_ENABLE_DANGEROUS_TOOLS` | `true` | Set to `false` if you want an additional kill-switch for `unlink`, `load`, and `call_method`. |
| `ODOO_MAX_LIMIT` | `500` | Max requested `limit`. |
| `ODOO_MAX_RECORDS` | `500` | Max returned records/ids from a handler. |
| `ODOO_MAX_PAYLOAD_BYTES` | `262144` | Max incoming tool payload size. |
| `ODOO_MAX_REPORT_BYTES` | `20000000` | Max decoded report size. |

Example opt-in mutation payload:

```json
{
  "model": "res.partner",
  "ids": [42],
  "values": {"comment": "Reviewed via MCP"},
  "confirm": true
}
```

To enable writes/mutations deliberately:

```bash
export ODOO_READ_ONLY=false
# Optional hardening:
export ODOO_ALLOWED_MODELS=res.partner,sale.order
export ODOO_ALLOWED_METHODS=action_confirm,button_cancel
```

## Available tools

Safe/read-oriented tools exposed in read-only mode:

- `ping`
- `models_list`
- `model_fields`
- `search`
- `read`
- `search_read` (requires `limit`)
- `name_search`
- `name_get`
- `read_group`
- `default_get`
- `onchange`
- `check_access_rights`
- `search_count`
- `export_data`
- `get_metadata`
- `report_download`

Mutation tools hidden/blocked in read-only mode and requiring `confirm=true` once read-only is disabled:

- `create`
- `write`
- `copy`
- `unlink`
- `load`
- `call_method`

## Docker

Build:

```bash
docker build -t odoo-mcp-server .
```

Run:

```bash
docker run -i --rm \
  -e ODOO_URL=https://your-instance.odoo.com \
  -e ODOO_DB=your_database \
  -e ODOO_USERNAME=your_username \
  -e ODOO_PASSWORD=your_password \
  -e ODOO_READ_ONLY=true \
  odoo-mcp-server
```

The container healthcheck imports the installed package by default. Set `ODOO_HEALTHCHECK_PING=true` to make it authenticate and call Odoo `version()` using the configured environment.

## Development

```bash
make lint
make type
make test
make check
```

Tests use mocks and do not require a live Odoo instance.

## License

MIT. See `LICENSE`.

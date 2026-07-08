# odoo-mcp-server

Secure Model Context Protocol (MCP) server for Odoo JSON-RPC.

The server exposes typed MCP tools for common Odoo read operations and guarded mutation tools for controlled administration. It is intentionally safe by default: read-only mode is enabled unless you opt in to mutations.

## Current status and limits

This project is useful for MCP-driven Odoo exploration and guarded automation, but it is not a blanket “complete Odoo API” proxy by default. Dangerous operations are disabled unless explicitly enabled and confirmed.

Implemented guardrails:

- `ODOO_READ_ONLY=true` by default; `READ_ONLY=true` is also accepted.
- Model allowlist via `ODOO_ALLOWED_MODELS` / `ALLOWED_MODELS` (glob patterns supported, default `*`).
- Method allowlist for `call_method` via `ODOO_ALLOWED_METHODS` / `ALLOWED_METHODS`.
- `unlink`, `load`, and `call_method` disabled by default via `ODOO_DISABLED_TOOLS` and `ODOO_ENABLE_DANGEROUS_TOOLS=false`.
- Mutating tools require `confirm=true` in the payload.
- Audit logs for mutations: user, tool, model, method, ids, approximate diff hash/fields.
- Model-name, method-name, domain, ids, limit, and sensitive-field validation.
- `search_read` requires an explicit `limit`; max limit defaults to 500.
- Secrets are redacted from structured logs.
- Synchronous Odoo RPC is run through `asyncio.to_thread` from async MCP handlers to avoid blocking the MCP event loop.

Known limits:

- The Odoo client still uses sync `httpx.Client`; a future version should migrate fully to `httpx.AsyncClient`.
- The local TTL cache is intentionally small and simple; it is not a distributed or bounded production cache.
- Allowlist defaults are permissive for read tools (`*` models) so existing read workflows continue to work; tighten them for production.

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
| `ODOO_ALLOWED_METHODS` / `ALLOWED_METHODS` | safe read methods | Comma-separated methods permitted for `call_method` when enabled. |
| `ODOO_DISABLED_TOOLS` / `DISABLED_TOOLS` | `unlink,load,call_method` | Tools hidden and blocked by policy. |
| `ODOO_ENABLE_DANGEROUS_TOOLS` | `false` | Required before `unlink`, `load`, or `call_method` can run. |
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

To enable dangerous tools deliberately:

```bash
export ODOO_READ_ONLY=false
export ODOO_ENABLE_DANGEROUS_TOOLS=true
export ODOO_DISABLED_TOOLS=
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

Mutation tools hidden in read-only mode and requiring `confirm=true`:

- `create`
- `write`
- `copy`
- `unlink` (dangerous, disabled by default)
- `load` (dangerous, disabled by default)
- `call_method` (dangerous, disabled by default)

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

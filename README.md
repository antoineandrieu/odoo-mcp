# MCP Odoo Server

MCP (Model Context Protocol) server exposing Odoo’s remote API (JSON-RPC/XML-RPC) as typed tools, useful resources, and ready-to-use prompts.

## Installation

- Python 3.10+
- `pip install -e .[dev]`
- Copy `.env.example` to `.env` and fill in your variables.

## Environment Variables

- `ODOO_URL` (e.g., https://odoo.example.com)
- `ODOO_DB`
- `ODOO_USERNAME`
- `ODOO_PASSWORD`
- `ODOO_TIMEOUT` (default 30)
- `ODOO_VERIFY_SSL` (true/false, default true)

## Run the MCP Server

- `make run`
- Or: `python -m odoo_mcp.mcp_server`

Example configuration (Claude Desktop):

```
{
  "mcpServers": {
    "odoo": {
      "command": "python",
      "args": ["-m", "odoo_mcp.mcp_server"],
      "env": {
        "ODOO_URL": "https://odoo.example.com",
        "ODOO_DB": "mydb",
        "ODOO_USERNAME": "admin",
        "ODOO_PASSWORD": "supersecret"
      }
    }
  }
}
```

## DX Scripts

- `make run`: start the MCP server (stdio)
- `make check`: ruff + mypy + pytest

## Available Tools

- `odoo.ping`: Verify connection (version + uid)
- `odoo.models.list`: List installed models
- `odoo.model.fields`: List fields of a model
- `odoo.search_read`: Search + read
- `odoo.create`: Create a record
- `odoo.write`: Update records
- `odoo.unlink`: Delete records
- `odoo.call_method`: Arbitrary call to `execute_kw`
- `odoo.report.download`: Generate/download report

## Resources

- `odoo/version`: Server + DB version + uid
- `odoo/models`: List of models (TTL 60s)
- `odoo/schema/{model}`: Detailed schema of a model (TTL 60s)

## Prompts

- `make_search_read_prompt`: turn a business description into `odoo.search_read`
- `write_values_prompt`: prepare a coherent `values` dict for `odoo.create`/`write`

## Tests

- `pytest`
- Unit tests for the client (httpx mocks) and tool handlers.

## Security & Logs

- Secrets loaded from env/.env, never logged.
- Structured logging with `request_id` correlation.

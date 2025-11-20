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
- Or: `python3 -m odoo_mcp.mcp_server`

Example configuration (Claude Desktop):

```json
{
  "mcpServers": {
    "odoo": {
      "command": "python3",
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

### Core Operations
- `odoo.ping`: Verify connection (version + uid)
- `odoo.models.list`: List installed models
- `odoo.model.fields`: List fields of a model

### CRUD Operations
- `odoo.search`: Search for record IDs matching a domain
- `odoo.read`: Read records by IDs
- `odoo.search_read`: Combined search + read (optimized)
- `odoo.create`: Create a new record
- `odoo.write`: Update existing records
- `odoo.unlink`: Delete records
- `odoo.copy`: Duplicate a record

### Advanced Search & Display
- `odoo.name_search`: Autocomplete-friendly name search
- `odoo.name_get`: Get display names for records
- `odoo.search_count`: Count records matching a domain
- `odoo.read_group`: Aggregate data with grouping (sum, count, avg, etc.)

### Form & UI Helpers
- `odoo.default_get`: Get default values for fields
- `odoo.onchange`: Simulate onchange behavior

### Access Control
- `odoo.check_access_rights`: Verify user permissions (read/write/create/unlink)

### Data Import/Export
- `odoo.export_data`: Export data in Odoo format
- `odoo.load`: Bulk import/load data

### Metadata & Reports
- `odoo.get_metadata`: Get creation/modification info
- `odoo.report.download`: Generate and download reports (PDF/XLSX)

### Generic Method Calls
- `odoo.call_method`: Call any Odoo model method via `execute_kw`

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

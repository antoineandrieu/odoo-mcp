# MCP Odoo Server

A powerful Model Context Protocol (MCP) server that exposes Odoo's complete API as typed tools, making it easy to interact with Odoo through Claude Desktop.

## ✨ Features

- **23 powerful tools** covering all Odoo operations
- **Fully typed** with Pydantic schemas and mypy strict mode
- **Production-ready** with retry logic, caching, and structured logging
- **Comprehensive** - CRUD, search, aggregations, reports, metadata, and more
- **Easy to install** with automated scripts and configuration helpers

## 🚀 Quick Start

### 1. Install

```bash
git clone <your-repo-url> odoo-mcp
cd odoo-mcp
chmod +x install.sh
./install.sh
```

The installation script will:
- ✓ Check Python version (3.10+ required)
- ✓ Create virtual environment
- ✓ Install all dependencies
- ✓ Guide you through configuration

### 2. Configure

Run the interactive configuration helper:

```bash
python3 configure.py
```

This will:
- Prompt for your Odoo credentials
- Generate the correct Claude Desktop configuration
- Show you exactly where to add it

**Or manually configure Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "odoo": {
      "command": "/absolute/path/to/odoo-mcp/.venv/bin/python",
      "args": ["-m", "odoo_mcp.mcp_server"],
      "env": {
        "ODOO_URL": "https://your-instance.odoo.com",
        "ODOO_DB": "your_database",
        "ODOO_USERNAME": "your_username",
        "ODOO_PASSWORD": "your_password"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

Quit and restart Claude Desktop to load the MCP server.

### 4. Test It

Ask Claude:
> "Can you ping the Odoo server?"

Claude should respond with your Odoo version and connection details!

## 🐳 Docker Installation (Alternative)

Build and run with Docker:

```bash
docker build -t odoo-mcp .
docker run -i \
  -e ODOO_URL=https://your-instance.odoo.com \
  -e ODOO_DB=your_database \
  -e ODOO_USERNAME=your_username \
  -e ODOO_PASSWORD=your_password \
  odoo-mcp
```

**Claude Desktop config for Docker:**
```json
{
  "mcpServers": {
    "odoo": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "ODOO_URL=https://your-instance.odoo.com",
        "-e", "ODOO_DB=your_database",
        "-e", "ODOO_USERNAME=your_username",
        "-e", "ODOO_PASSWORD=your_password",
        "odoo-mcp"
      ]
    }
  }
}
```

## ⚙️ Environment Variables

- `ODOO_URL` - Your Odoo instance URL (e.g., https://mycompany.odoo.com)
- `ODOO_DB` - Database name
- `ODOO_USERNAME` - Odoo username
- `ODOO_PASSWORD` - Odoo password
- `ODOO_TIMEOUT` - Request timeout in seconds (default: 30)
- `ODOO_VERIFY_SSL` - Verify SSL certificates (default: true)
- `LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)

## 🛠️ Development

### Commands

- `make run` - Start the MCP server (stdio mode)
- `make check` - Run all checks (ruff + mypy + pytest)
- `make lint` - Run ruff linting
- `make type` - Run mypy type checking
- `make test` - Run pytest

### Manual Testing

```bash
source .venv/bin/activate
python3 -m odoo_mcp.mcp_server
```

The server will start and wait for MCP connections via stdin/stdout.

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

## 🧪 Testing

```bash
source .venv/bin/activate
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest --cov=src         # With coverage report
```

All tests use mocks - no real Odoo instance required for development.

## 🔒 Security

- **Never commit credentials** - Use `.env` or environment variables
- **SSL verification enabled** by default (set `ODOO_VERIFY_SSL=false` only for development)
- **Passwords never logged** - Structured logging sanitizes sensitive fields
- **Read-only users recommended** - Create dedicated Odoo users with minimal permissions

## 📊 Logging

Structured JSON logging with request correlation:

```json
{
  "level": "INFO",
  "logger": "odoo_mcp.mcp_server",
  "message": "odoo.search_read",
  "time": "2024-11-20T14:30:00",
  "request_id": "abc-123",
  "model": "res.partner",
  "count": 42
}
```

Set `LOG_LEVEL=DEBUG` for detailed debugging.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run `make check` to ensure quality
5. Submit a pull request

## 📝 License

[Add your license here]

## 🆘 Troubleshooting

**Server not connecting?**
- Check Claude Desktop logs: `~/Library/Logs/Claude/mcp*.log`
- Verify absolute paths in config
- Test manually: `python3 -m odoo_mcp.mcp_server`

**Authentication errors?**
- Verify credentials in Odoo web interface
- Check database name (case-sensitive)
- Ensure URL includes `https://` or `http://`

**SSL certificate issues?**
- For development: set `ODOO_VERIFY_SSL=false`
- For production: fix certificates or use proper CA

**Timeout issues?**
- Increase timeout: `"ODOO_TIMEOUT": "60"`

**Multiple Odoo instances?**
- Add multiple entries in `mcpServers` with different names
- Each can point to a different Odoo instance

# Dockerfile for Odoo MCP Server
# Build: docker build -t odoo-mcp .
# Run: docker run -i -e ODOO_URL=... -e ODOO_DB=... -e ODOO_USERNAME=... -e ODOO_PASSWORD=... odoo-mcp

FROM python:3.12-slim

LABEL maintainer="MCP Odoo <devnull@example.com>"
LABEL description="Model Context Protocol server for Odoo"

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Environment variables with defaults
ENV ODOO_URL="" \
    ODOO_DB="" \
    ODOO_USERNAME="" \
    ODOO_PASSWORD="" \
    ODOO_TIMEOUT=30 \
    ODOO_VERIFY_SSL=true \
    LOG_LEVEL=INFO

# Health check (basic validation that Python imports work)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python3 -c "import odoo_mcp" || exit 1

# Run as non-root user for security
RUN useradd -m -u 1000 mcpuser && \
    chown -R mcpuser:mcpuser /app
USER mcpuser

# Run the MCP server
# Note: MCP uses stdio, so we use -i for interactive mode
ENTRYPOINT ["python3", "-m", "odoo_mcp.mcp_server"]

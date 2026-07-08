# Build: docker build -t odoo-mcp-server .
# Run: docker run -i -e ODOO_URL=... -e ODOO_DB=... -e ODOO_USERNAME=... -e ODOO_PASSWORD=... odoo-mcp-server

FROM python:3.12-slim-bookworm AS builder

WORKDIR /build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir .

FROM python:3.12-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="odoo-mcp-server"
LABEL org.opencontainers.image.description="Secure Model Context Protocol server for guarded Odoo RPC access"

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ODOO_TIMEOUT=30 \
    ODOO_VERIFY_SSL=true \
    ODOO_READ_ONLY=true \
    LOG_LEVEL=INFO

COPY --from=builder /opt/venv /opt/venv

RUN useradd -m -u 1000 mcpuser
USER mcpuser
WORKDIR /home/mcpuser

# Default healthcheck verifies the installed package. Set ODOO_HEALTHCHECK_PING=true
# to also authenticate and call Odoo version() with the configured env credentials.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import odoo_mcp" && \
    if [ "${ODOO_HEALTHCHECK_PING:-false}" = "true" ]; then \
      python -c "from odoo_mcp.config import Settings; from odoo_mcp.odoo_client import OdooClient, OdooClientConfig; s=Settings(); c=OdooClient(OdooClientConfig(str(s.url), s.db, s.username, s.password, s.timeout, s.verify_ssl)); c.authenticate(); c.version(); c.close()"; \
    fi

ENTRYPOINT ["odoo-mcp-server"]

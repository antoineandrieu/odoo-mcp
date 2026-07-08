from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from odoo_mcp.config import Settings
from odoo_mcp.mcp_server import create_http_app


def configured_settings(monkeypatch: pytest.MonkeyPatch, **env: str) -> Settings:
    values = {
        "ODOO_URL": "https://odoo.example.com",
        "ODOO_DB": "db",
        "ODOO_USERNAME": "user",
        "ODOO_PASSWORD": "pass",
        **env,
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return Settings()  # type: ignore[call-arg]


def test_default_transport_is_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = configured_settings(monkeypatch)
    assert settings.mcp_transport == "stdio"
    assert settings.mcp_path == "/mcp"


def test_http_transport_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = configured_settings(
        monkeypatch,
        ODOO_MCP_TRANSPORT="streamable-http",
        ODOO_MCP_HOST="0.0.0.0",
        ODOO_MCP_PORT="9000",
        ODOO_MCP_PATH="/odoo/mcp",
        ODOO_MCP_AUTH_TOKEN="secret",
    )
    assert settings.mcp_transport == "streamable-http"
    assert settings.mcp_host == "0.0.0.0"
    assert settings.mcp_port == 9000
    assert settings.mcp_path == "/odoo/mcp"
    assert settings.safe_dict()["mcp_auth_token"] == "***"


def test_streamable_http_app_healthz(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = configured_settings(monkeypatch, ODOO_MCP_TRANSPORT="http")
    app = create_http_app(settings)
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "transport": "streamable-http"}


def test_streamable_http_app_optional_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = configured_settings(monkeypatch, ODOO_MCP_AUTH_TOKEN="secret")
    app = create_http_app(settings)
    with TestClient(app) as client:
        response = client.get(settings.mcp_path)
    assert response.status_code == 401
    assert response.json() == {"error": "missing or invalid bearer token"}

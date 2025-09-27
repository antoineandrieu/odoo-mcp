from __future__ import annotations

import json
from typing import Any, Dict

import httpx
import pytest

from odoo_mcp.odoo_client import OdooClient, OdooClientConfig


class MockResponse:
    def __init__(self, status_code: int, json_data: Dict[str, Any]) -> None:
        self.status_code = status_code
        self._json = json_data

    def json(self) -> Dict[str, Any]:
        return self._json


class MockClient:
    def __init__(self) -> None:
        self.calls: list[Dict[str, Any]] = []

    def post(self, path: str, content: str) -> MockResponse:  # type: ignore[override]
        data = json.loads(content)
        self.calls.append({"path": path, "data": data})
        params = data["params"]
        service = params["service"]
        method = params["method"]
        args = params["args"]
        if service == "common" and method == "login":
            return MockResponse(200, {"result": 42})
        if service == "common" and method == "version":
            return MockResponse(200, {"result": {"server_version": "16.0"}})
        if service == "object" and method == "execute_kw":
            # args = [db, uid, pwd, model, method, args, kwargs]
            model = args[3]
            meth = args[4]
            if model == "res.partner" and meth == "search_count":
                return MockResponse(200, {"result": 2})
            if model == "res.partner" and meth == "search_read":
                return MockResponse(200, {"result": [{"id": 1}, {"id": 2}]})
        return MockResponse(500, {"error": {"code": 500, "message": "Unhandled"}})

    def close(self) -> None:  # noqa: D401
        pass


def test_auth_and_search_read(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = OdooClientConfig(
        base_url="https://odoo.example.com",
        db="db",
        username="admin",
        password="x",
        timeout=5,
        verify_ssl=True,
    )
    client = OdooClient(cfg)
    mock = MockClient()
    monkeypatch.setattr(client, "_http", mock)
    uid = client.authenticate()
    assert uid == 42
    ver = client.version()
    assert ver["server_version"] == "16.0"
    count, records = client.search_read("res.partner", [])
    assert count == 2
    assert len(records) == 2


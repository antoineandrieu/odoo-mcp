from __future__ import annotations

from typing import Any

import pytest

from odoo_mcp import mcp_server
from odoo_mcp.errors import OdooSecurityError
from odoo_mcp.schemas import (
    CallMethodIn,
    CreateIn,
    ModelFieldsIn,
    ModelsListIn,
    ReportDownloadIn,
    SearchReadIn,
    UnlinkIn,
    WriteIn,
)


class FakeSettings:
    username = "tester@example.com"
    read_only = False
    allowed_models = "res.partner,ir.model"
    allowed_methods = "check"
    enable_dangerous_tools = True
    max_limit = 500
    max_records = 500
    max_payload_bytes = 262_144
    max_report_bytes = 20_000_000

    @property
    def disabled_tools_set(self) -> set[str]:
        return set()


class FakeClient:
    def __init__(self) -> None:
        self.uid = 7

    def version(self) -> dict[str, Any]:
        return {"server_version": "17.0"}

    def models_list(
        self, *, search: str | None = None, limit: int = 50, offset: int = 0
    ) -> tuple[int, list[dict[str, Any]]]:
        return 1, [{"model": "res.partner", "name": "Contact"}]

    def fields_get(self, model: str) -> dict[str, Any]:
        return {"name": {"type": "char", "required": False, "readonly": False}}

    def search_read(
        self,
        model: str,
        domain: list[Any],
        *,
        fields: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order: str | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        return 1, [{"id": 1, "name": "X"}]

    def create(self, model: str, values: dict[str, Any]) -> int:
        return 99

    def write(self, model: str, ids: list[int], values: dict[str, Any]) -> int:
        return len(ids)

    def unlink(self, model: str, ids: list[int]) -> int:
        return len(ids)

    def execute_kw(
        self,
        model: str,
        method: str,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        return {"ok": True}

    def report_download(
        self, report_name: str, ids: list[int], fmt: str = "pdf"
    ) -> tuple[str, str, str]:
        return ("rep.pdf", "application/pdf", "UEs=")


@pytest.fixture(autouse=True)
def patch_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mcp_server, "get_client", lambda: FakeClient())
    monkeypatch.setattr(mcp_server, "get_settings", lambda: FakeSettings())


@pytest.mark.asyncio
async def test_tools_handlers() -> None:
    ping = await mcp_server.handle_ping()
    assert ping.uid == 7

    models = await mcp_server.handle_models_list(ModelsListIn(limit=50, offset=0).model_dump())
    assert models.total == 1

    fields = await mcp_server.handle_model_fields(ModelFieldsIn(model="res.partner").model_dump())
    assert fields.model == "res.partner"
    assert fields.fields[0].name == "name"

    sr = await mcp_server.handle_search_read(
        SearchReadIn(model="res.partner", domain=[], limit=10, offset=0).model_dump()
    )
    assert sr.count == 1

    cr = await mcp_server.handle_create(
        CreateIn(model="res.partner", values={"name": "X"}, confirm=True).model_dump()
    )
    assert cr.id == 99

    wr = await mcp_server.handle_write(
        WriteIn(model="res.partner", ids=[1, 2], values={"name": "Y"}, confirm=True).model_dump()
    )
    assert wr["updated"] == 2

    ur = await mcp_server.handle_unlink(
        UnlinkIn(model="res.partner", ids=[1], confirm=True).model_dump()
    )
    assert ur["deleted"] == 1

    cm = await mcp_server.handle_call_method(
        CallMethodIn(model="res.partner", method="check", confirm=True).model_dump()
    )
    assert cm.result["ok"] is True

    rep = await mcp_server.handle_report_download(
        ReportDownloadIn(report_name="x", ids=[1], format="pdf").model_dump()
    )
    assert rep.filename.endswith(".pdf")


@pytest.mark.asyncio
async def test_mutation_requires_confirmation() -> None:
    with pytest.raises(OdooSecurityError, match="confirm=true"):
        await mcp_server.handle_write(
            WriteIn(model="res.partner", ids=[1], values={"name": "Y"}).model_dump()
        )

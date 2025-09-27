from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pytest

from odoo_mcp import mcp_server
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


class FakeClient:
    def __init__(self) -> None:
        self.uid = 7

    def version(self) -> Dict[str, Any]:
        return {"server_version": "17.0"}

    def models_list(self, *, search: str | None = None, limit: int = 50, offset: int = 0) -> Tuple[int, List[Dict[str, Any]]]:
        return 1, [{"model": "res.partner", "name": "Contact"}]

    def fields_get(self, model: str) -> Dict[str, Any]:
        return {"name": {"type": "char", "required": False, "readonly": False}}

    def search_read(self, model: str, domain: List[Any], *, fields: List[str] | None = None, limit: int | None = None, offset: int | None = None, order: str | None = None) -> Tuple[int, List[Dict[str, Any]]]:  # type: ignore[override]
        return 1, [{"id": 1, "name": "X"}]

    def create(self, model: str, values: Dict[str, Any]) -> int:
        return 99

    def write(self, model: str, ids: List[int], values: Dict[str, Any]) -> int:
        return len(ids)

    def unlink(self, model: str, ids: List[int]) -> int:
        return len(ids)

    def execute_kw(self, model: str, method: str, args: List[Any] | None = None, kwargs: Dict[str, Any] | None = None) -> Any:  # noqa: D401
        return {"ok": True}

    def report_download(self, report_name: str, ids: List[int], fmt: str = "pdf") -> tuple[str, str, str]:  # noqa: D401
        return ("rep.pdf", "application/pdf", "UEs=")


@pytest.fixture(autouse=True)
def patch_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mcp_server, "get_client", lambda: FakeClient())


@pytest.mark.asyncio
async def test_tools_handlers() -> None:
    ping = await mcp_server.handle_ping()
    assert ping.uid == 7

    models = await mcp_server.handle_models_list(ModelsListIn().model_dump())
    assert models.total == 1

    fields = await mcp_server.handle_model_fields(ModelFieldsIn(model="res.partner").model_dump())
    assert fields.model == "res.partner"
    assert fields.fields[0].name == "name"

    sr = await mcp_server.handle_search_read(SearchReadIn(model="res.partner", domain=[]).model_dump())
    assert sr.count == 1

    cr = await mcp_server.handle_create(CreateIn(model="res.partner", values={"name": "X"}).model_dump())
    assert cr.id == 99

    wr = await mcp_server.handle_write2(WriteIn(model="res.partner", ids=[1, 2], values={"name": "Y"}).model_dump())
    assert wr["updated"] == 2

    ur = await mcp_server.handle_unlink(UnlinkIn(model="res.partner", ids=[1]).model_dump())
    assert ur["deleted"] == 1

    cm = await mcp_server.handle_call_method(CallMethodIn(model="res.partner", method="check").model_dump())
    assert cm.result["ok"] is True

    rep = await mcp_server.handle_report_download(ReportDownloadIn(report_name="x", ids=[1]).model_dump())
    assert rep.filename.endswith(".pdf")


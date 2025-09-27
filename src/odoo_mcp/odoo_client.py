from __future__ import annotations

import base64
import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import httpx
from tenacity import RetryError, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .errors import OdooAuthError, OdooRPCError, TransientOdooError


logger = logging.getLogger(__name__)


class TTLCache:
    def __init__(self, ttl_seconds: int = 60) -> None:
        self.ttl = ttl_seconds
        self._store: dict[tuple[Any, ...], tuple[float, Any]] = {}

    def get(self, key: Iterable[Any]) -> Any | None:
        k = tuple(key)
        item = self._store.get(k)
        if not item:
            return None
        expire, value = item
        if time.time() > expire:
            self._store.pop(k, None)
            return None
        return value

    def set(self, key: Iterable[Any], value: Any) -> None:
        self._store[tuple(key)] = (time.time() + self.ttl, value)


@dataclass
class OdooClientConfig:
    base_url: str
    db: str
    username: str
    password: str
    timeout: int = 30
    verify_ssl: bool = True


class OdooClient:
    """Lightweight Odoo RPC client with JSON-RPC primary and XML-RPC fallback."""

    def __init__(self, cfg: OdooClientConfig) -> None:
        self.cfg = cfg
        self._http = httpx.Client(
            base_url=cfg.base_url,
            timeout=cfg.timeout,
            verify=cfg.verify_ssl,
            headers={"Content-Type": "application/json"},
        )
        self._uid: Optional[int] = None
        self._models_cache = TTLCache(60)
        self._fields_cache = TTLCache(60)

    @property
    def uid(self) -> int:
        if self._uid is None:
            raise OdooAuthError("Not authenticated")
        return self._uid

    def close(self) -> None:
        self._http.close()

    # Retries for transient network/server errors
    def _transient_exc(self, exc: BaseException) -> bool:
        return isinstance(exc, (httpx.ReadTimeout, httpx.ConnectError, TransientOdooError))

    @retry(
        reraise=True,
        retry=retry_if_exception_type((httpx.ReadTimeout, httpx.ConnectError, TransientOdooError)),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        stop=stop_after_attempt(5),
    )
    def _jsonrpc(self, service: str, method: str, args: list[Any]) -> Any:
        req_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"service": service, "method": method, "args": args},
            "id": req_id,
        }
        resp = self._http.post("/jsonrpc", content=json.dumps(payload))
        if resp.status_code >= 500:
            logger.warning("odoo.jsonrpc.5xx", status=resp.status_code, id=req_id)
            raise TransientOdooError(f"Server error {resp.status_code}")
        if resp.status_code != 200:
            raise OdooRPCError(f"HTTP {resp.status_code} on /jsonrpc", code=resp.status_code)
        data = resp.json()
        if "error" in data:
            err = data["error"]
            code = err.get("code")
            message = err.get("message") or "Odoo RPC error"
            if code and 500 <= int(code) < 600:
                raise TransientOdooError(message, code=code, data=err)
            raise OdooRPCError(message, code=code, data=err)
        return data.get("result")

    def authenticate(self) -> int:
        try:
            uid = self._jsonrpc("common", "login", [self.cfg.db, self.cfg.username, self.cfg.password])
        except RetryError as re:  # from tenacity
            raise OdooAuthError("Authentication failed (retries exhausted)") from re
        if not isinstance(uid, int):
            raise OdooAuthError("Authentication failed: invalid uid")
        self._uid = uid
        return uid

    def version(self) -> Mapping[str, Any]:
        res = self._jsonrpc("common", "version", [])
        if not isinstance(res, dict):
            raise OdooRPCError("Invalid version payload")
        return res

    def execute_kw(
        self, model: str, method: str, args: Optional[List[Any]] = None, kwargs: Optional[Dict[str, Any]] = None
    ) -> Any:
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        return self._jsonrpc(
            "object",
            "execute_kw",
            [self.cfg.db, self.uid, self.cfg.password, model, method, args, kwargs],
        )

    def models_list(self, *, search: Optional[str] = None, limit: int = 50, offset: int = 0) -> Tuple[int, List[Dict[str, Any]]]:
        cache_key = (search or "", limit, offset)
        cached = self._models_cache.get(cache_key)
        if cached is not None:
            return cached
        domain: List[Any] = []
        if search:
            domain = [["model", "ilike", search]]
        total = self.execute_kw("ir.model", "search_count", [domain])
        ids = self.execute_kw("ir.model", "search", [domain], {"limit": limit, "offset": offset, "order": "model asc"})
        items = self.execute_kw("ir.model", "read", [ids, ["model", "name"]]) if ids else []
        result = (int(total), list(items))
        self._models_cache.set(cache_key, result)
        return result

    def fields_get(self, model: str) -> Dict[str, Any]:
        cached = self._fields_cache.get((model,))
        if cached is not None:
            return cached
        fields = self.execute_kw(model, "fields_get", [], {"attributes": ["string", "type", "required", "readonly", "relation"]})
        self._fields_cache.set((model,), fields)
        return fields

    def search_read(
        self,
        model: str,
        domain: List[Any],
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order: Optional[str] = None,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        kwargs: Dict[str, Any] = {}
        if fields is not None:
            kwargs["fields"] = fields
        if limit is not None:
            kwargs["limit"] = limit
        if offset is not None:
            kwargs["offset"] = offset
        if order is not None:
            kwargs["order"] = order
        count = int(self.execute_kw(model, "search_count", [domain]))
        records: List[Dict[str, Any]] = []
        if count:
            records = list(self.execute_kw(model, "search_read", [domain], kwargs))
        return count, records

    def create(self, model: str, values: Dict[str, Any]) -> int:
        new_id = self.execute_kw(model, "create", [values])
        return int(new_id)

    def write(self, model: str, ids: List[int], values: Dict[str, Any]) -> int:
        ok = bool(self.execute_kw(model, "write", [ids, values]))
        return len(ids) if ok else 0

    def unlink(self, model: str, ids: List[int]) -> int:
        ok = bool(self.execute_kw(model, "unlink", [ids]))
        return len(ids) if ok else 0

    def report_download(self, report_name: str, ids: List[int], fmt: str = "pdf") -> tuple[str, str, str]:
        mimetype = "application/pdf" if fmt == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        # Try a common method via ir.actions.report (Odoo >= 14)
        try:
            data = self.execute_kw(
                "ir.actions.report",
                "render_report",
                [],
                {"report_name": report_name, "docids": ids, "data": {}, "report_type": fmt},
            )
        except OdooRPCError:
            # Fallback: many instances expose 'report' service; not guaranteed.
            data = self._jsonrpc("report", "render_report", [self.cfg.db, report_name, ids])
        if isinstance(data, (list, tuple)) and len(data) >= 1:
            raw = data[0]
        else:
            raw = data
        if isinstance(raw, str):
            # Might already be base64
            try:
                base64.b64decode(raw, validate=True)
                content_b64 = raw
            except Exception:
                content_b64 = base64.b64encode(raw.encode()).decode()
        elif isinstance(raw, (bytes, bytearray)):
            content_b64 = base64.b64encode(raw).decode()
        else:
            # Unknown payload
            content = json.dumps(raw).encode()
            content_b64 = base64.b64encode(content).decode()
        filename = f"{report_name}.{fmt}"
        return filename, mimetype, content_b64


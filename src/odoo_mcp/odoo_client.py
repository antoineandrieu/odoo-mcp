from __future__ import annotations

import base64
import json
import logging
import time
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .errors import OdooAuthError, OdooRPCError, OdooValidationError, TransientOdooError

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
            follow_redirects=True,
        )
        self._uid: int | None = None
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
        logger.debug(
            "odoo.jsonrpc.request",
            extra={"request_id": req_id, "payload": self._redact(payload)},
        )
        resp = self._http.post("/jsonrpc", content=json.dumps(payload))
        if resp.status_code >= 500:
            logger.warning("odoo.jsonrpc.5xx", extra={"status": resp.status_code, "id": req_id})
            raise TransientOdooError(f"Server error {resp.status_code}")
        if resp.status_code != 200:
            raise OdooRPCError(f"HTTP {resp.status_code} on /jsonrpc", code=resp.status_code)
        data = resp.json()
        if "error" in data:
            err = self._normalize_error(data["error"])
            code = err.get("code")
            message = str(err.get("message") or "Odoo RPC error")
            logger.warning(
                "odoo.jsonrpc.error",
                extra={"request_id": req_id, "error": err, "service": service, "method": method},
            )
            if code and isinstance(code, int) and 500 <= code < 600:
                raise TransientOdooError(message, code=code, data=err)
            error_name = str(err.get("name", ""))
            if "AccessDenied" in error_name or "AccessError" in error_name:
                raise OdooAuthError(message, code=code, data=err)
            if "ValidationError" in error_name or "UserError" in error_name:
                raise OdooValidationError(message, code=code, data=err)
            raise OdooRPCError(message, code=code, data=err)
        return data.get("result")

    def _normalize_error(self, err: Mapping[str, Any]) -> dict[str, Any]:
        raw_data = err.get("data")
        data: Mapping[str, Any] = raw_data if isinstance(raw_data, Mapping) else {}
        return {
            "code": err.get("code"),
            "message": err.get("message") or data.get("message"),
            "name": data.get("name"),
            "debug": data.get("debug"),
            "arguments": data.get("arguments"),
            "exception_type": data.get("exception_type"),
        }

    def _redact(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): "***"
                if any(
                    part in str(key).lower()
                    for part in ("password", "token", "api_key", "private_key")
                )
                else self._redact(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        return value

    def authenticate(self) -> int:
        try:
            uid = self._jsonrpc(
                "common", "login", [self.cfg.db, self.cfg.username, self.cfg.password]
            )
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
        self,
        model: str,
        method: str,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
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

    def models_list(
        self, *, search: str | None = None, limit: int = 50, offset: int = 0
    ) -> tuple[int, list[dict[str, Any]]]:
        cache_key = (search or "", limit, offset)
        cached = self._models_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]
        domain: list[Any] = []
        if search:
            domain = [["model", "ilike", search]]
        total = self.execute_kw("ir.model", "search_count", [domain])
        ids = self.execute_kw(
            "ir.model", "search", [domain], {"limit": limit, "offset": offset, "order": "model asc"}
        )
        items = self.execute_kw("ir.model", "read", [ids, ["model", "name"]]) if ids else []
        result = (int(total), list(items))
        self._models_cache.set(cache_key, result)
        return result

    def fields_get(self, model: str) -> dict[str, Any]:
        cached = self._fields_cache.get((model,))
        if cached is not None:
            return cached  # type: ignore[no-any-return]
        fields: dict[str, Any] = self.execute_kw(
            model,
            "fields_get",
            [],
            {"attributes": ["string", "type", "required", "readonly", "relation"]},
        )
        self._fields_cache.set((model,), fields)
        return fields

    def search_read(
        self,
        model: str,
        domain: list[Any],
        fields: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order: str | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        kwargs: dict[str, Any] = {}
        if fields is not None:
            kwargs["fields"] = fields
        if limit is not None:
            kwargs["limit"] = limit
        if offset is not None:
            kwargs["offset"] = offset
        if order is not None:
            kwargs["order"] = order
        count = int(self.execute_kw(model, "search_count", [domain]))
        records: list[dict[str, Any]] = []
        if count:
            records = list(self.execute_kw(model, "search_read", [domain], kwargs))
        return count, records

    def create(self, model: str, values: dict[str, Any]) -> int:
        new_id = self.execute_kw(model, "create", [values])
        return int(new_id)

    def write(self, model: str, ids: list[int], values: dict[str, Any]) -> int:
        ok = bool(self.execute_kw(model, "write", [ids, values]))
        return len(ids) if ok else 0

    def unlink(self, model: str, ids: list[int]) -> int:
        ok = bool(self.execute_kw(model, "unlink", [ids]))
        return len(ids) if ok else 0

    def report_download(
        self, report_name: str, ids: list[int], fmt: str = "pdf"
    ) -> tuple[str, str, str]:
        mimetype = (
            "application/pdf"
            if fmt == "pdf"
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
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
        raw = data[0] if isinstance(data, (list, tuple)) and len(data) >= 1 else data
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

    def name_search(
        self, model: str, name: str = "", domain: list[Any] | None = None, limit: int = 100
    ) -> list[tuple[int, str]]:
        """Search for records by name and return [(id, display_name), ...]."""
        if domain is None:
            domain = []
        result: list[tuple[int, str]] = self.execute_kw(
            model, "name_search", [], {"name": name, "args": domain, "limit": limit}
        )
        return result

    def name_get(self, model: str, ids: list[int]) -> list[tuple[int, str]]:
        """Get display names for records."""
        result: list[tuple[int, str]] = self.execute_kw(model, "name_get", [ids])
        return result

    def read_group(
        self,
        model: str,
        domain: list[Any],
        fields: list[str],
        groupby: list[str],
        offset: int = 0,
        limit: int | None = None,
        orderby: str | None = None,
        lazy: bool = True,
    ) -> list[dict[str, Any]]:
        """Aggregate data grouped by specified fields."""
        kwargs: dict[str, Any] = {
            "fields": fields,
            "groupby": groupby,
            "offset": offset,
            "lazy": lazy,
        }
        if limit is not None:
            kwargs["limit"] = limit
        if orderby is not None:
            kwargs["orderby"] = orderby
        result: list[dict[str, Any]] = self.execute_kw(model, "read_group", [domain], kwargs)
        return result

    def default_get(self, model: str, fields: list[str]) -> dict[str, Any]:
        """Get default values for fields."""
        result: dict[str, Any] = self.execute_kw(model, "default_get", [fields])
        return result

    def onchange(
        self,
        model: str,
        ids: list[int],
        values: dict[str, Any],
        field_name: str,
        field_onchange: dict[str, str],
    ) -> dict[str, Any]:
        """Simulate onchange behavior."""
        result: dict[str, Any] = self.execute_kw(
            model, "onchange", [ids, values, field_name, field_onchange]
        )
        return result

    def check_access_rights(
        self, model: str, operation: str, raise_exception: bool = False
    ) -> bool:
        """Check if user has access rights for operation (read/write/create/unlink)."""
        result: bool = self.execute_kw(
            model, "check_access_rights", [operation], {"raise_exception": raise_exception}
        )
        return result

    def search_count(self, model: str, domain: list[Any]) -> int:
        """Count records matching domain."""
        result: int = self.execute_kw(model, "search_count", [domain])
        return result

    def copy(self, model: str, record_id: int, default: dict[str, Any] | None = None) -> int:
        """Duplicate a record."""
        kwargs = {"default": default} if default else {}
        result: int = self.execute_kw(model, "copy", [record_id], kwargs)
        return result

    def export_data(
        self, model: str, ids: list[int], fields: list[str], raw_data: bool = False
    ) -> dict[str, Any]:
        """Export data for specified records and fields."""
        result: dict[str, Any] = self.execute_kw(
            model, "export_data", [ids, fields], {"raw_data": raw_data}
        )
        return result

    def load(self, model: str, fields: list[str], data: list[list[Any]]) -> dict[str, Any]:
        """Import/load data (bulk create/update)."""
        result: dict[str, Any] = self.execute_kw(model, "load", [fields, data])
        return result

    def get_metadata(self, model: str, ids: list[int]) -> list[dict[str, Any]]:
        """Get metadata (create/write info) for records."""
        result: list[dict[str, Any]] = self.execute_kw(model, "get_metadata", [ids])
        return result

    def search(
        self,
        model: str,
        domain: list[Any],
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
    ) -> list[int]:
        """Search for record IDs matching domain."""
        kwargs: dict[str, Any] = {"offset": offset}
        if limit is not None:
            kwargs["limit"] = limit
        if order is not None:
            kwargs["order"] = order
        result: list[int] = self.execute_kw(model, "search", [domain], kwargs)
        return result

    def read(
        self, model: str, ids: list[int], fields: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Read records by IDs."""
        kwargs = {"fields": fields} if fields else {}
        result: list[dict[str, Any]] = self.execute_kw(model, "read", [ids], kwargs)
        return result

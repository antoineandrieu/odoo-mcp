from __future__ import annotations

import fnmatch
import hashlib
import json
import logging
from collections.abc import Mapping, Sequence
from typing import Any

from .config import Settings
from .errors import OdooSecurityError, OdooValidationError

logger = logging.getLogger(__name__)

SENSITIVE_FIELD_FRAGMENTS = ("password", "token", "api_key", "private_key")


def parse_csv(value: str | Sequence[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def is_allowed_name(name: str, patterns: Sequence[str]) -> bool:
    if not patterns:
        return False
    return any(pattern == "*" or fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def assert_model_allowed(settings: Settings, model: str) -> None:
    allowed = parse_csv(settings.allowed_models)
    if not is_allowed_name(model, allowed):
        raise OdooSecurityError(
            f"Model {model!r} is not in ODOO_ALLOWED_MODELS allowlist",
            code="model_not_allowed",
        )


def assert_method_allowed(settings: Settings, method: str) -> None:
    allowed = parse_csv(settings.allowed_methods)
    if not is_allowed_name(method, allowed):
        raise OdooSecurityError(
            f"Method {method!r} is not in ODOO_ALLOWED_METHODS allowlist",
            code="method_not_allowed",
        )


def assert_tool_enabled(settings: Settings, tool_name: str) -> None:
    if tool_name in settings.disabled_tools_set:
        raise OdooSecurityError(f"Tool {tool_name!r} is disabled", code="tool_disabled")
    if tool_name in {"unlink", "load", "call_method"} and not settings.enable_dangerous_tools:
        raise OdooSecurityError(
            f"Tool {tool_name!r} is blocked by ODOO_ENABLE_DANGEROUS_TOOLS=false",
            code="dangerous_tool_disabled",
        )


def assert_mutation_allowed(
    settings: Settings,
    *,
    tool_name: str,
    model: str,
    method: str,
    confirm: bool,
) -> None:
    assert_tool_enabled(settings, tool_name)
    assert_model_allowed(settings, model)
    if settings.read_only:
        raise OdooSecurityError(
            "Mutating operations are blocked while READ_ONLY/ODOO_READ_ONLY is true",
            code="read_only",
        )
    if not confirm:
        raise OdooSecurityError(
            "Mutating operations require confirm=true in the tool payload",
            code="confirmation_required",
        )
    if tool_name == "call_method":
        assert_method_allowed(settings, method)


def sensitive_field_name(field_name: str) -> bool:
    lowered = field_name.lower()
    return any(fragment in lowered for fragment in SENSITIVE_FIELD_FRAGMENTS)


def blocked_sensitive_fields(fields: Sequence[str] | None) -> list[str]:
    if not fields:
        return []
    return sorted({field for field in fields if sensitive_field_name(field)})


def assert_no_sensitive_fields(fields: Sequence[str] | None) -> None:
    blocked = blocked_sensitive_fields(fields)
    if blocked:
        raise OdooValidationError(
            f"Sensitive fields are blocked by default: {', '.join(blocked)}",
            code="sensitive_fields_blocked",
        )


def redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "***" if sensitive_field_name(str(key)) else redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    return value


def approx_diff(
    values: Mapping[str, Any] | None = None, fields: Sequence[str] | None = None
) -> dict[str, Any]:
    if values is not None:
        redacted = redact_value(values)
        serialized = json.dumps(redacted, sort_keys=True, default=str)
        return {
            "changed_fields": sorted(str(key) for key in values),
            "payload_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
        }
    if fields is not None:
        return {"fields": list(fields), "rows": None}
    return {}


def audit_log(
    *,
    settings: Settings,
    request_id: str,
    tool_name: str,
    model: str,
    method: str,
    ids: Sequence[int] | None = None,
    diff: Mapping[str, Any] | None = None,
) -> None:
    logger.info(
        "odoo.audit",
        extra={
            "request_id": request_id,
            "user": settings.username,
            "tool": tool_name,
            "model": model,
            "method": method,
            "ids": list(ids or []),
            "diff": dict(diff or {}),
        },
    )

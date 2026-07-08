from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any


class JsonFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        # Avoid logging huge payloads by truncating extras
        if hasattr(record, "payload"):
            payload = record.payload
            try:
                text = json.dumps(payload)
            except Exception:
                text = str(payload)
            if len(text) > 2000:
                record.payload = text[:2000] + "…<truncated>"
        return True


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "***"
            if any(
                part in str(key).lower() for part in ("password", "token", "api_key", "private_key")
            )
            else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        base: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }
        base_vars = vars(logging.LogRecord("", 0, "", 0, "", (), None))
        extra = {k: v for k, v in record.__dict__.items() if k not in base_vars}
        # Sanitize secrets
        for key in list(extra.keys()):
            if any(s in key.lower() for s in ("password", "token", "authorization", "api_key")):
                extra[key] = "***"
            else:
                extra[key] = redact(extra[key])
        base.update(extra)
        return json.dumps(base, ensure_ascii=False)


def setup_logging(level: int | str | None = None) -> None:
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    logging.captureWarnings(True)
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stderr)
    handler.addFilter(JsonFilter())
    handler.setFormatter(JsonFormatter())
    root.handlers = [handler]

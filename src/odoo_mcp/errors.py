from __future__ import annotations

from typing import Any

ErrorCode = int | str


class OdooError(Exception):
    """Base error for Odoo client failures."""

    code: ErrorCode | None

    def __init__(
        self, message: str, *, code: ErrorCode | None = None, data: Any | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.data = data

    def to_mcp_error(self, *, request_id: str | None = None) -> dict[str, Any]:
        return {
            "error": {
                "type": self.__class__.__name__,
                "code": self.code,
                "message": str(self),
                "request_id": request_id,
                "data": self.data,
            }
        }


class OdooAuthError(OdooError):
    """Authentication failed."""


class OdooRPCError(OdooError):
    """Generic RPC error from Odoo (JSON-RPC/XML-RPC)."""


class OdooNotFoundError(OdooError):
    """Requested model/record not found."""


class OdooValidationError(OdooError):
    """Invalid input payload for Odoo operation."""


class OdooSecurityError(OdooValidationError):
    """Request blocked by the MCP security policy before reaching Odoo."""


class TransientOdooError(OdooError):
    """Transient error (retryable)."""

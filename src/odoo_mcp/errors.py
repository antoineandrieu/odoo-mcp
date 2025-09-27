from __future__ import annotations

from typing import Any, Optional


class OdooError(Exception):
    """Base error for Odoo client failures."""

    code: Optional[int]

    def __init__(self, message: str, *, code: Optional[int] = None, data: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.data = data


class OdooAuthError(OdooError):
    """Authentication failed."""


class OdooRPCError(OdooError):
    """Generic RPC error from Odoo (JSON-RPC/XML-RPC)."""


class OdooNotFoundError(OdooError):
    """Requested model/record not found."""


class OdooValidationError(OdooError):
    """Invalid input payload for Odoo operation."""


class TransientOdooError(OdooError):
    """Transient error (retryable)."""


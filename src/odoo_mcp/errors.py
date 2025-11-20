from __future__ import annotations

from typing import Any


class OdooError(Exception):
    """Base error for Odoo client failures."""

    code: int | None

    def __init__(self, message: str, *, code: int | None = None, data: Any | None = None) -> None:
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


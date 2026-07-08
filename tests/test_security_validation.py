from __future__ import annotations

import pytest
from pydantic import ValidationError

from odoo_mcp.config import Settings
from odoo_mcp.errors import OdooSecurityError
from odoo_mcp.schemas import SearchReadIn, WriteIn
from odoo_mcp.security import assert_method_allowed, assert_model_allowed, assert_mutation_allowed


def configured_settings(monkeypatch: pytest.MonkeyPatch, **env: str) -> Settings:
    values = {
        "ODOO_URL": "https://odoo.example.com",
        "ODOO_DB": "db",
        "ODOO_USERNAME": "user",
        "ODOO_PASSWORD": "pass",
        **env,
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return Settings()  # type: ignore[call-arg]


def test_search_read_requires_explicit_limit() -> None:
    with pytest.raises(ValidationError):
        SearchReadIn.model_validate({"model": "res.partner", "domain": [], "offset": 0})


def test_model_name_validation_blocks_bad_characters() -> None:
    with pytest.raises(ValidationError):
        SearchReadIn(model="res.partner;drop", domain=[], limit=10, offset=0)


def test_domain_validator_rejects_unknown_operator() -> None:
    with pytest.raises(ValidationError):
        SearchReadIn(model="res.partner", domain=[["name", "contains", "x"]], limit=10, offset=0)


def test_sensitive_fields_blocked_in_fields_and_values() -> None:
    with pytest.raises(ValidationError):
        SearchReadIn(model="res.partner", domain=[], fields=["password"], limit=10, offset=0)

    with pytest.raises(ValidationError):
        WriteIn(model="res.partner", ids=[1], values={"api_key": "secret"})


def test_settings_accept_read_only_without_odoo_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("READ_ONLY", "true")
    settings = configured_settings(monkeypatch)
    assert settings.read_only is True


def test_default_policy_is_read_only_but_allows_models_methods_and_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = configured_settings(monkeypatch)
    assert settings.read_only is True
    assert settings.allowed_models == "*"
    assert settings.allowed_methods == "*"
    assert settings.disabled_tools_set == set()
    assert settings.enable_dangerous_tools is True

    assert_model_allowed(settings, "sale.order")
    assert_method_allowed(settings, "action_confirm")


def test_allowlist_and_read_only_policy_blocks_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = configured_settings(monkeypatch, ODOO_ALLOWED_MODELS="res.partner")

    assert_model_allowed(settings, "res.partner")
    with pytest.raises(OdooSecurityError, match="not in .* allowlist"):
        assert_model_allowed(settings, "sale.order")

    with pytest.raises(OdooSecurityError, match="READ_ONLY"):
        assert_mutation_allowed(
            settings,
            tool_name="write",
            model="res.partner",
            method="write",
            confirm=True,
        )

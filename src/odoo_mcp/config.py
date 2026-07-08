from __future__ import annotations

from pydantic import AliasChoices, AnyHttpUrl, Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment.

    Secrets must not be logged. Use `safe_dict()` for logging/sanitization.
    """

    # Maps ODOO_URL -> url, ODOO_DB -> db, etc.
    model_config = SettingsConfigDict(env_prefix="ODOO_", env_file=".env", case_sensitive=False)

    url: AnyHttpUrl
    db: str
    username: str
    password: str
    timeout: int = 30
    verify_ssl: bool = True
    read_only: bool = Field(True, validation_alias=AliasChoices("ODOO_READ_ONLY", "READ_ONLY"))
    allowed_models: str = Field(
        "*", validation_alias=AliasChoices("ODOO_ALLOWED_MODELS", "ALLOWED_MODELS")
    )
    allowed_methods: str = Field(
        "*", validation_alias=AliasChoices("ODOO_ALLOWED_METHODS", "ALLOWED_METHODS")
    )
    disabled_tools: str = Field(
        "", validation_alias=AliasChoices("ODOO_DISABLED_TOOLS", "DISABLED_TOOLS")
    )
    enable_dangerous_tools: bool = Field(
        True,
        validation_alias=AliasChoices("ODOO_ENABLE_DANGEROUS_TOOLS", "ENABLE_DANGEROUS_TOOLS"),
    )
    max_limit: int = Field(500, ge=1, le=5000)
    max_records: int = Field(500, ge=1, le=10000)
    max_payload_bytes: int = Field(262_144, ge=1024)
    max_report_bytes: int = Field(20_000_000, ge=1024)

    @field_validator("db", "username", "password")
    @classmethod
    def not_empty(cls, v: str, info: ValidationInfo) -> str:
        if not v:
            raise ValueError(f"{info.field_name} cannot be empty")
        return v

    def safe_dict(self) -> dict[str, object]:
        return {
            "url": str(self.url),
            "db": self.db,
            "username": self.username,
            "password": "***",
            "timeout": self.timeout,
            "verify_ssl": self.verify_ssl,
            "read_only": self.read_only,
            "allowed_models": self.allowed_models,
            "allowed_methods": self.allowed_methods,
            "disabled_tools": self.disabled_tools,
            "enable_dangerous_tools": self.enable_dangerous_tools,
            "max_limit": self.max_limit,
            "max_records": self.max_records,
            "max_payload_bytes": self.max_payload_bytes,
            "max_report_bytes": self.max_report_bytes,
        }

    @property
    def disabled_tools_set(self) -> set[str]:
        return {tool.strip() for tool in self.disabled_tools.split(",") if tool.strip()}

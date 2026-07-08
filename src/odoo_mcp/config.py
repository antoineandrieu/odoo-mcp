from __future__ import annotations

from typing import Literal

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
    mcp_transport: Literal["stdio", "http", "streamable-http"] = Field(
        "stdio",
        validation_alias=AliasChoices("ODOO_MCP_TRANSPORT", "MCP_TRANSPORT", "ODOO_TRANSPORT"),
    )
    mcp_host: str = Field(
        "127.0.0.1", validation_alias=AliasChoices("ODOO_MCP_HOST", "MCP_HOST")
    )
    mcp_port: int = Field(
        8765, ge=1, le=65535, validation_alias=AliasChoices("ODOO_MCP_PORT", "MCP_PORT")
    )
    mcp_path: str = Field("/mcp", validation_alias=AliasChoices("ODOO_MCP_PATH", "MCP_PATH"))
    mcp_stateless_http: bool = Field(
        False, validation_alias=AliasChoices("ODOO_MCP_STATELESS_HTTP", "MCP_STATELESS_HTTP")
    )
    mcp_json_response: bool = Field(
        False, validation_alias=AliasChoices("ODOO_MCP_JSON_RESPONSE", "MCP_JSON_RESPONSE")
    )
    mcp_auth_token: str | None = Field(
        None, validation_alias=AliasChoices("ODOO_MCP_AUTH_TOKEN", "MCP_AUTH_TOKEN")
    )
    mcp_allowed_hosts: str = Field(
        "127.0.0.1,localhost", validation_alias=AliasChoices("ODOO_MCP_ALLOWED_HOSTS")
    )
    mcp_allowed_origins: str = Field(
        "", validation_alias=AliasChoices("ODOO_MCP_ALLOWED_ORIGINS")
    )

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
            "mcp_transport": self.mcp_transport,
            "mcp_host": self.mcp_host,
            "mcp_port": self.mcp_port,
            "mcp_path": self.mcp_path,
            "mcp_stateless_http": self.mcp_stateless_http,
            "mcp_json_response": self.mcp_json_response,
            "mcp_auth_token": "***" if self.mcp_auth_token else None,
            "mcp_allowed_hosts": self.mcp_allowed_hosts,
            "mcp_allowed_origins": self.mcp_allowed_origins,
        }

    @property
    def disabled_tools_set(self) -> set[str]:
        return {tool.strip() for tool in self.disabled_tools.split(",") if tool.strip()}

    @field_validator("mcp_path")
    @classmethod
    def path_starts_with_slash(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("mcp_path must start with '/'")
        return value

    @property
    def mcp_allowed_hosts_list(self) -> list[str]:
        return [host.strip() for host in self.mcp_allowed_hosts.split(",") if host.strip()]

    @property
    def mcp_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.mcp_allowed_origins.split(",") if origin.strip()]

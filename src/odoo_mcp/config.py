from __future__ import annotations

from pydantic import AnyHttpUrl, ValidationInfo, field_validator
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
        }

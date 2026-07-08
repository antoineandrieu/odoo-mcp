from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

MAX_LIMIT = 500
MAX_IDS = 500
MODEL_RE = re.compile(r"^[a-zA-Z0-9_.]+$")
METHOD_RE = re.compile(r"^[a-zA-Z0-9_]+$")
SENSITIVE_FIELD_FRAGMENTS = ("password", "token", "api_key", "private_key")
DOMAIN_OPERATORS = {
    "=",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "like",
    "not like",
    "=like",
    "ilike",
    "not ilike",
    "=ilike",
    "in",
    "not in",
    "child_of",
    "parent_of",
    "=?",
}
DOMAIN_LOGICAL_OPERATORS = {"&", "|", "!"}


def _is_sensitive_field(field: str) -> bool:
    lowered = field.lower()
    return any(fragment in lowered for fragment in SENSITIVE_FIELD_FRAGMENTS)


def _assert_safe_fields(fields: list[str] | None) -> None:
    if not fields:
        return
    blocked = sorted({field for field in fields if _is_sensitive_field(field)})
    if blocked:
        raise ValueError(f"Sensitive fields are blocked: {', '.join(blocked)}")


def _validate_domain_leaf(item: Any) -> None:
    if not isinstance(item, (list, tuple)) or len(item) != 3:
        raise ValueError("Domain leaves must be [field, operator, value] triples")
    field, operator, _value = item
    if not isinstance(field, str) or not field or _is_sensitive_field(field):
        raise ValueError("Domain field names must be non-sensitive strings")
    if not isinstance(operator, str) or operator not in DOMAIN_OPERATORS:
        raise ValueError(f"Unsupported Odoo domain operator: {operator!r}")


def _validate_domain(domain: Any) -> list[Any]:
    if not isinstance(domain, list):
        raise ValueError("Odoo domain must be a list")
    for item in domain:
        if isinstance(item, str):
            if item not in DOMAIN_LOGICAL_OPERATORS:
                raise ValueError(f"Unsupported Odoo domain logical token: {item!r}")
            continue
        if isinstance(item, (list, tuple)) and item and item[0] in DOMAIN_LOGICAL_OPERATORS:
            _validate_domain(list(item))
            continue
        _validate_domain_leaf(item)
    return domain


def _validate_ids(ids: list[int]) -> list[int]:
    if len(ids) > MAX_IDS:
        raise ValueError(f"Too many ids requested; max is {MAX_IDS}")
    return ids


def _validate_values(values: dict[str, Any] | None) -> dict[str, Any] | None:
    if values is not None:
        _assert_safe_fields([str(key) for key in values])
    return values


class OdooModelIn(BaseModel):
    @field_validator("model", check_fields=False)
    @classmethod
    def valid_model_name(cls, value: str) -> str:
        if not MODEL_RE.fullmatch(value):
            raise ValueError("Invalid Odoo model name")
        return value

    @field_validator("domain", check_fields=False)
    @classmethod
    def valid_domain(cls, value: list[Any]) -> list[Any]:
        return _validate_domain(value)

    @field_validator("fields", check_fields=False)
    @classmethod
    def safe_field_list(cls, value: list[str] | None) -> list[str] | None:
        _assert_safe_fields(value)
        return value

    @field_validator("ids", check_fields=False)
    @classmethod
    def sane_ids(cls, value: list[int]) -> list[int]:
        return _validate_ids(value)

    @field_validator("values", "default", check_fields=False)
    @classmethod
    def safe_values(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return _validate_values(value)

    @field_validator("limit", check_fields=False)
    @classmethod
    def bounded_limit(cls, value: int | None) -> int | None:
        if value is not None and value > MAX_LIMIT:
            raise ValueError(f"limit must be <= {MAX_LIMIT}")
        return value


class PingOut(BaseModel):
    server_version: str
    uid: int


class ModelsListIn(OdooModelIn):
    limit: int = Field(50, ge=0, le=MAX_LIMIT)
    offset: int = Field(0, ge=0)
    search: str | None = None


class ModelItem(BaseModel):
    model: str
    name: str | None = None


class ModelsListOut(BaseModel):
    total: int
    items: list[ModelItem]


class ModelFieldsIn(OdooModelIn):
    model: str


class FieldInfo(BaseModel):
    name: str
    ttype: str
    required: bool
    readonly: bool
    relation: str | None = None


class ModelFieldsOut(BaseModel):
    model: str
    fields: list[FieldInfo]


class SearchReadIn(OdooModelIn):
    model: str
    domain: list[Any] = Field(default_factory=list)
    fields: list[str] | None = None
    limit: int = Field(..., ge=1, le=MAX_LIMIT)
    offset: int | None = Field(None, ge=0)
    order: str | None = None


class SearchReadOut(BaseModel):
    count: int
    records: list[dict[str, Any]]


class CreateIn(OdooModelIn):
    model: str
    values: dict[str, Any]
    confirm: bool = False


class CreateOut(BaseModel):
    id: int


class WriteIn(OdooModelIn):
    model: str
    ids: list[int]
    values: dict[str, Any]
    confirm: bool = False


class WriteOut(BaseModel):
    updated: int


class UnlinkIn(OdooModelIn):
    model: str
    ids: list[int]
    confirm: bool = False


class UnlinkOut(BaseModel):
    deleted: int


class CallMethodIn(OdooModelIn):
    model: str
    method: str
    args: list[Any] | None = None
    kwargs: dict[str, Any] | None = None
    confirm: bool = False

    @field_validator("method")
    @classmethod
    def valid_method_name(cls, value: str) -> str:
        if not METHOD_RE.fullmatch(value):
            raise ValueError("Invalid Odoo method name")
        return value


class CallMethodOut(BaseModel):
    result: Any


class ReportDownloadIn(BaseModel):
    report_name: str
    ids: list[int]
    format: Literal["pdf", "xlsx"] | None = Field("pdf")

    @field_validator("ids")
    @classmethod
    def sane_ids(cls, value: list[int]) -> list[int]:
        return _validate_ids(value)


class ReportDownloadOut(BaseModel):
    filename: str
    mimetype: str
    content_b64: str


class NameSearchIn(OdooModelIn):
    model: str
    name: str = ""
    domain: list[Any] = Field(default_factory=list)
    limit: int = Field(100, ge=1, le=MAX_LIMIT)


class NameSearchOut(BaseModel):
    results: list[tuple[int, str]]


class NameGetIn(OdooModelIn):
    model: str
    ids: list[int]


class NameGetOut(BaseModel):
    results: list[tuple[int, str]]


class ReadGroupIn(OdooModelIn):
    model: str
    domain: list[Any] = Field(default_factory=list)
    fields: list[str]
    groupby: list[str]
    offset: int = Field(0, ge=0)
    limit: int | None = Field(None, ge=1, le=MAX_LIMIT)
    orderby: str | None = None
    lazy: bool = True


class ReadGroupOut(BaseModel):
    results: list[dict[str, Any]]


class DefaultGetIn(OdooModelIn):
    model: str
    fields: list[str]


class DefaultGetOut(BaseModel):
    defaults: dict[str, Any]


class OnchangeIn(OdooModelIn):
    model: str
    ids: list[int]
    values: dict[str, Any]
    field_name: str
    field_onchange: dict[str, str]


class OnchangeOut(BaseModel):
    result: dict[str, Any]


class CheckAccessRightsIn(OdooModelIn):
    model: str
    operation: Literal["read", "write", "create", "unlink"]
    raise_exception: bool = False


class CheckAccessRightsOut(BaseModel):
    has_access: bool


class SearchCountIn(OdooModelIn):
    model: str
    domain: list[Any] = Field(default_factory=list)


class SearchCountOut(BaseModel):
    count: int


class CopyIn(OdooModelIn):
    model: str
    record_id: int
    default: dict[str, Any] | None = None
    confirm: bool = False


class CopyOut(BaseModel):
    new_id: int


class ExportDataIn(OdooModelIn):
    model: str
    ids: list[int]
    fields: list[str]
    raw_data: bool = False


class ExportDataOut(BaseModel):
    result: dict[str, Any]


class LoadDataIn(OdooModelIn):
    model: str
    fields: list[str]
    data: list[list[Any]]
    confirm: bool = False


class LoadDataOut(BaseModel):
    result: dict[str, Any]


class GetMetadataIn(OdooModelIn):
    model: str
    ids: list[int]


class GetMetadataOut(BaseModel):
    metadata: list[dict[str, Any]]


class SearchIn(OdooModelIn):
    model: str
    domain: list[Any] = Field(default_factory=list)
    offset: int = Field(0, ge=0)
    limit: int | None = Field(None, ge=1, le=MAX_LIMIT)
    order: str | None = None


class SearchOut(BaseModel):
    ids: list[int]


class ReadIn(OdooModelIn):
    model: str
    ids: list[int]
    fields: list[str] | None = None


class ReadOut(BaseModel):
    records: list[dict[str, Any]]

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class PingOut(BaseModel):
    server_version: str
    uid: int


class ModelsListIn(BaseModel):
    limit: int = Field(50, ge=0)
    offset: int = Field(0, ge=0)
    search: str | None = None


class ModelItem(BaseModel):
    model: str
    name: str | None = None


class ModelsListOut(BaseModel):
    total: int
    items: list[ModelItem]


class ModelFieldsIn(BaseModel):
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


class SearchReadIn(BaseModel):
    model: str
    domain: list[Any] = Field(default_factory=list)
    fields: list[str] | None = None
    limit: int | None = Field(None, ge=0)
    offset: int | None = Field(None, ge=0)
    order: str | None = None


class SearchReadOut(BaseModel):
    count: int
    records: list[dict[str, Any]]


class CreateIn(BaseModel):
    model: str
    values: dict[str, Any]


class CreateOut(BaseModel):
    id: int


class WriteIn(BaseModel):
    model: str
    ids: list[int]
    values: dict[str, Any]


class WriteOut(BaseModel):
    updated: int


class UnlinkIn(BaseModel):
    model: str
    ids: list[int]


class UnlinkOut(BaseModel):
    deleted: int


class CallMethodIn(BaseModel):
    model: str
    method: str
    args: list[Any] | None = None
    kwargs: dict[str, Any] | None = None


class CallMethodOut(BaseModel):
    result: Any


class ReportDownloadIn(BaseModel):
    report_name: str
    ids: list[int]
    format: Literal["pdf", "xlsx"] | None = Field("pdf")


class ReportDownloadOut(BaseModel):
    filename: str
    mimetype: str
    content_b64: str


class NameSearchIn(BaseModel):
    model: str
    name: str = ""
    domain: list[Any] = Field(default_factory=list)
    limit: int = Field(100, ge=1)


class NameSearchOut(BaseModel):
    results: list[tuple[int, str]]


class NameGetIn(BaseModel):
    model: str
    ids: list[int]


class NameGetOut(BaseModel):
    results: list[tuple[int, str]]


class ReadGroupIn(BaseModel):
    model: str
    domain: list[Any] = Field(default_factory=list)
    fields: list[str]
    groupby: list[str]
    offset: int = Field(0, ge=0)
    limit: int | None = Field(None, ge=1)
    orderby: str | None = None
    lazy: bool = True


class ReadGroupOut(BaseModel):
    results: list[dict[str, Any]]


class DefaultGetIn(BaseModel):
    model: str
    fields: list[str]


class DefaultGetOut(BaseModel):
    defaults: dict[str, Any]


class OnchangeIn(BaseModel):
    model: str
    ids: list[int]
    values: dict[str, Any]
    field_name: str
    field_onchange: dict[str, str]


class OnchangeOut(BaseModel):
    result: dict[str, Any]


class CheckAccessRightsIn(BaseModel):
    model: str
    operation: Literal["read", "write", "create", "unlink"]
    raise_exception: bool = False


class CheckAccessRightsOut(BaseModel):
    has_access: bool


class SearchCountIn(BaseModel):
    model: str
    domain: list[Any] = Field(default_factory=list)


class SearchCountOut(BaseModel):
    count: int


class CopyIn(BaseModel):
    model: str
    record_id: int
    default: dict[str, Any] | None = None


class CopyOut(BaseModel):
    new_id: int


class ExportDataIn(BaseModel):
    model: str
    ids: list[int]
    fields: list[str]
    raw_data: bool = False


class ExportDataOut(BaseModel):
    result: dict[str, Any]


class LoadDataIn(BaseModel):
    model: str
    fields: list[str]
    data: list[list[Any]]


class LoadDataOut(BaseModel):
    result: dict[str, Any]


class GetMetadataIn(BaseModel):
    model: str
    ids: list[int]


class GetMetadataOut(BaseModel):
    metadata: list[dict[str, Any]]


class SearchIn(BaseModel):
    model: str
    domain: list[Any] = Field(default_factory=list)
    offset: int = Field(0, ge=0)
    limit: int | None = Field(None, ge=1)
    order: str | None = None


class SearchOut(BaseModel):
    ids: list[int]


class ReadIn(BaseModel):
    model: str
    ids: list[int]
    fields: list[str] | None = None


class ReadOut(BaseModel):
    records: list[dict[str, Any]]


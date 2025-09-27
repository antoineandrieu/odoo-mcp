from __future__ import annotations

from typing import Any, Dict, List, Optional

from typing import Literal

from pydantic import BaseModel, Field


class PingOut(BaseModel):
    server_version: str
    uid: int


class ModelsListIn(BaseModel):
    limit: int = Field(50, ge=0)
    offset: int = Field(0, ge=0)
    search: Optional[str] = None


class ModelItem(BaseModel):
    model: str
    name: Optional[str] = None


class ModelsListOut(BaseModel):
    total: int
    items: List[ModelItem]


class ModelFieldsIn(BaseModel):
    model: str


class FieldInfo(BaseModel):
    name: str
    ttype: str
    required: bool
    readonly: bool
    relation: Optional[str] = None


class ModelFieldsOut(BaseModel):
    model: str
    fields: List[FieldInfo]


class SearchReadIn(BaseModel):
    model: str
    domain: List[Any] = Field(default_factory=list)
    fields: Optional[List[str]] = None
    limit: Optional[int] = Field(None, ge=0)
    offset: Optional[int] = Field(None, ge=0)
    order: Optional[str] = None


class SearchReadOut(BaseModel):
    count: int
    records: List[Dict[str, Any]]


class CreateIn(BaseModel):
    model: str
    values: Dict[str, Any]


class CreateOut(BaseModel):
    id: int


class WriteIn(BaseModel):
    model: str
    ids: List[int]
    values: Dict[str, Any]


class WriteOut(BaseModel):
    updated: int


class UnlinkIn(BaseModel):
    model: str
    ids: List[int]


class UnlinkOut(BaseModel):
    deleted: int


class CallMethodIn(BaseModel):
    model: str
    method: str
    args: Optional[List[Any]] = None
    kwargs: Optional[Dict[str, Any]] = None


class CallMethodOut(BaseModel):
    result: Any


class ReportDownloadIn(BaseModel):
    report_name: str
    ids: List[int]
    format: Optional[Literal["pdf", "xlsx"]] = Field("pdf")


class ReportDownloadOut(BaseModel):
    filename: str
    mimetype: str
    content_b64: str


from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from typing import Optional


T = TypeVar("T")


class ResponseMeta(BaseModel):
    requestId: str
    generatedAt: str


class ErrorSchema(BaseModel):
    code: str
    message: str
    statusCode: int


class ResponseEnvelope(BaseModel, Generic[T]):
    data: Optional[T]
    meta: ResponseMeta
    error: Optional[ErrorSchema] = None


class PaginationSchema(BaseModel):
    page: int
    pageSize: int
    totalItems: int
    totalPages: int


def make_response(data: Any, request_id: str) -> dict:
    return {
        "data": data,
        "meta": {
            "requestId": request_id,
            "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
        "error": None,
    }


def make_error_response(code: str, message: str, status_code: int, request_id: str) -> dict:
    return {
        "data": None,
        "meta": {
            "requestId": request_id,
            "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
        "error": {"code": code, "message": message, "statusCode": status_code},
    }


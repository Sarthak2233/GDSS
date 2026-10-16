from typing import Any

from pydantic import BaseModel, Field


class APIResponseBase(BaseModel):
    version: str = "1.0"
    timestamp: str
    repo: str
    status: str = "ok"
    warnings: list[str] = Field(default_factory=list)

class ErrorDetails(BaseModel):
    what: str
    why: str
    fix: str

class APIError(BaseModel):
    code: str
    details: ErrorDetails

class ErrorResponse(BaseModel):
    error: APIError

class StatusResponse(APIResponseBase):
    data: dict[str, Any]

class GraphResponse(APIResponseBase):
    data: dict[str, Any]

class DriftResponse(APIResponseBase):
    data: dict[str, Any]

class AlertsResponse(APIResponseBase):
    data: dict[str, Any]

class LogResponse(APIResponseBase):
    data: list[dict[str, Any]]

class SimilarResponse(APIResponseBase):
    data: dict[str, Any]

class HealthResponse(BaseModel):
    version: str = "1.0"
    status: str = "ok"
    repo: str | None = None

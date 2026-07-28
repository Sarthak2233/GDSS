from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class APIResponseBase(BaseModel):
    version: str = "1.0"
    timestamp: str
    repo: str
    status: str = "ok"
    warnings: List[str] = Field(default_factory=list)

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
    data: Dict[str, Any]

class GraphResponse(APIResponseBase):
    data: Dict[str, Any]

class DriftResponse(APIResponseBase):
    data: Dict[str, Any]

class AlertsResponse(APIResponseBase):
    data: Dict[str, Any]

class LogResponse(APIResponseBase):
    data: List[Dict[str, Any]]

class SimilarResponse(APIResponseBase):
    data: Dict[str, Any]

class HealthResponse(BaseModel):
    version: str = "1.0"
    status: str = "ok"

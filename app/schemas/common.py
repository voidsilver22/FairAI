from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    detail: str
    code: str


class HealthResponse(BaseModel):
    status: str
    environment: str
    storage_backend: str
    queue_backend: str
    compute_backend: str
    time: datetime


class MetadataResponse(BaseModel):
    service: str
    version: str
    environment: str
    supported_metrics: int
    execution_modes: list[str]
    adapters: dict[str, str]
    optional_integrations: dict[str, Any] = Field(default_factory=dict)


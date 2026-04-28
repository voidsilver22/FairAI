from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HostedScoreRequest(BaseModel):
    job_id: str
    resume_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class HostedScoreResponse(BaseModel):
    job_id: str
    score: float
    prediction: int
    model_name: str
    notes: list[str]


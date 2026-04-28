from __future__ import annotations

from pydantic import BaseModel


class MetricDefinitionResponse(BaseModel):
    key: str
    name: str
    description: str
    threshold: float
    comparator: str
    regulation_refs: list[str]
    implementation_status: str
    notes: str | None = None


class MetricCatalogResponse(BaseModel):
    metrics: list[MetricDefinitionResponse]


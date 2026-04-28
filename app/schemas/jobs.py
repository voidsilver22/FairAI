from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.domain import AsyncJobRecord, AuditInputSpec
from app.models.enums import ExecutionMode


class DebiasJobConfig(BaseModel):
    resume_text_column: str | None = None
    label_column: str
    positive_label: str | int | float | bool = 1
    protected_attributes: list[str]
    conditional_attributes: list[str] = Field(default_factory=list)
    fairness_weight: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_input_spec(self, default_fairness_weight: float, *, file_uri: str | None) -> AuditInputSpec:
        return AuditInputSpec(
            source_uri=file_uri,
            resume_text_column=self.resume_text_column,
            label_column=self.label_column,
            positive_label=self.positive_label,
            protected_attributes=self.protected_attributes,
            conditional_attributes=self.conditional_attributes,
            fairness_weight=self.fairness_weight or default_fairness_weight,
            execution_mode=ExecutionMode.QUEUED,
            metadata=self.metadata,
        )


class DebiasJobRequest(BaseModel):
    file_uri: str
    config: DebiasJobConfig

    def to_input_spec(self, default_fairness_weight: float) -> AuditInputSpec:
        return self.config.to_input_spec(default_fairness_weight, file_uri=self.file_uri)


class JobSubmitRequest(DebiasJobConfig):
    source_uri: str

    def to_debias_request(self) -> DebiasJobRequest:
        return DebiasJobRequest(
            file_uri=self.source_uri,
            config=DebiasJobConfig.model_validate(self.model_dump(exclude={"source_uri"})),
        )


class JobAcceptedResponse(BaseModel):
    job_id: str
    status: Literal["accepted"] = "accepted"
    status_url: str | None = None


class JobSubmitResponse(JobAcceptedResponse):
    pass


class JobStatusResponse(BaseModel):
    job: AsyncJobRecord


class JobListResponse(BaseModel):
    jobs: list[AsyncJobRecord]


class InlinePipelineRequest(DebiasJobConfig):
    records: list[dict[str, Any]]

    def to_input_spec(self, default_fairness_weight: float) -> AuditInputSpec:
        return super().to_input_spec(default_fairness_weight, file_uri=None)


class InlinePipelineResponse(JobAcceptedResponse):
    pass

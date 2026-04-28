from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    ArtifactKind,
    ExecutionMode,
    JobStatus,
    PipelineStage,
    Severity,
    UploadStatus,
)


class StatusEvent(BaseModel):
    status: JobStatus
    stage: PipelineStage
    message: str
    timestamp: datetime


class UploadRecord(BaseModel):
    upload_id: str
    filename: str
    content_type: str
    artifact_uri: str
    upload_url: str
    storage_mode: str
    headers: dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    expires_at: datetime
    status: UploadStatus


class ArtifactRecord(BaseModel):
    kind: ArtifactKind
    artifact_uri: str
    filename: str
    content_type: str
    description: str
    created_at: datetime
    size_bytes: int | None = None


class AuditInputSpec(BaseModel):
    source_uri: str | None = None
    source_type: str = "csv"
    resume_text_column: str | None = None
    label_column: str
    positive_label: str | int | float | bool
    protected_attributes: list[str]
    conditional_attributes: list[str] = Field(default_factory=list)
    fairness_weight: float
    execution_mode: ExecutionMode = ExecutionMode.SYNC
    job_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DatasetProfile(BaseModel):
    row_count: int
    column_count: int
    columns: list[str]
    resume_text_column: str
    protected_attribute_values: dict[str, list[str]]
    positive_rate: float


class MetricResult(BaseModel):
    metric_key: str
    metric_name: str
    stage: str
    protected_attribute: str
    group_a: str
    group_b: str
    value: float
    threshold: float
    passed: bool
    severity: Severity
    human_summary: str
    regulation_refs: list[str] = Field(default_factory=list)
    notes: str | None = None


class FeatureAttribution(BaseModel):
    protected_attribute: str
    feature_name: str
    disparity_score: float
    baseline_contribution_gap: float
    verification_contribution_gap: float
    explanation: str


class CounterfactualFlip(BaseModel):
    row_index: int
    original_group: str
    alternative_group: str
    original_prediction: int
    alternative_prediction: int


class CounterfactualAudit(BaseModel):
    protected_attribute: str
    stage: str
    flip_rate: float
    sample_size: int
    severity: Severity
    examples: list[CounterfactualFlip] = Field(default_factory=list)


class ModelPerformance(BaseModel):
    accuracy: float
    precision: float
    recall: float
    positive_rate: float


class DebiasingIteration(BaseModel):
    iteration: int
    predictor_loss: float
    adversary_signal: float
    fairness_penalty: float


class RemediationSummary(BaseModel):
    strategy: str
    fairness_weight: float
    iterations: list[DebiasingIteration]
    notes: str


class LinearModelArtifact(BaseModel):
    model_name: str
    intercept: float
    coefficients: dict[str, float]
    feature_means: dict[str, float]
    feature_stds: dict[str, float]
    threshold: float = 0.5


class FairnessReport(BaseModel):
    job_id: str
    created_at: datetime
    dataset_profile: DatasetProfile
    baseline_performance: ModelPerformance
    verification_performance: ModelPerformance
    baseline_metrics: list[MetricResult]
    verification_metrics: list[MetricResult]
    counterfactuals: list[CounterfactualAudit]
    feature_attributions: list[FeatureAttribution]
    remediation: RemediationSummary
    summary: dict[str, Any]
    cloud_hooks: dict[str, Any] = Field(default_factory=dict)


class AsyncJobRecord(BaseModel):
    job_id: str
    status: JobStatus
    file_uri: str
    config: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AuditJobRecord(BaseModel):
    job_id: str
    created_at: datetime
    updated_at: datetime
    status: JobStatus
    stage: PipelineStage
    input_spec: AuditInputSpec
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    report: FairnessReport | None = None
    cloud_hooks: dict[str, Any] = Field(default_factory=dict)
    status_history: list[StatusEvent] = Field(default_factory=list)
    error_message: str | None = None

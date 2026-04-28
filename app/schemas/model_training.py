from __future__ import annotations

from pydantic import BaseModel, Field


class ModelTrainingFileInfo(BaseModel):
    key: str
    name: str
    path: str
    category: str
    exists: bool
    size_bytes: int | None = None


class ModelTrainingWorkspaceResponse(BaseModel):
    workspace_path: str
    exists: bool
    capabilities: dict[str, bool]
    files: list[ModelTrainingFileInfo]
    generated_report_available: bool
    report_models: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ModelTrainingDatasetBuildRequest(BaseModel):
    input_filename: str = "fairlens_dataset_structured.csv"
    output_filename: str = "fairlens_dataset_unstructured.csv"


class ModelTrainingDatasetBuildResponse(BaseModel):
    input_path: str
    output_path: str
    row_count: int
    columns: list[str]


class ModelTrainingMetric(BaseModel):
    name: str
    value: float
    threshold: float
    passed: bool
    description: str


class ModelTrainingEvaluatedGroup(BaseModel):
    attribute: str
    privileged: str
    unprivileged: str


class ModelTrainingAuditSlice(BaseModel):
    audit_status: str
    evaluated_group: ModelTrainingEvaluatedGroup
    metrics: list[ModelTrainingMetric]


class ModelTrainingAuditBundle(BaseModel):
    Baseline: dict[str, ModelTrainingAuditSlice]
    FairLens: dict[str, ModelTrainingAuditSlice]


class ModelTrainingAuditRequest(BaseModel):
    baseline_results_filename: str = "baseline_scored_results.csv"
    fairlens_results_filename: str = "clean_scored_results.csv"
    baseline_score_column: str = "Model_Predicted_Score"
    fairlens_score_column: str = "FairLens_Predicted_Score"
    baseline_threshold: float = 0.70
    fairlens_threshold: float = 0.685
    output_filename: str = "final_audit_report.json"


class ModelTrainingAuditResponse(BaseModel):
    output_path: str
    report: ModelTrainingAuditBundle

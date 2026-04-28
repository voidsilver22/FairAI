from __future__ import annotations

from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStage(str, Enum):
    RECEIVED = "received"
    INGESTION = "ingestion"
    SCRUBBING = "scrubbing"
    FEATURE_EXTRACTION = "feature_extraction"
    BASELINE_AUDIT = "baseline_audit"
    DEBIASING = "debiasing"
    VERIFICATION = "verification"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ArtifactKind(str, Enum):
    UPLOAD = "upload"
    SCRUBBED_DATASET = "scrubbed_dataset"
    FEATURE_FRAME = "feature_frame"
    BASELINE_REPORT = "baseline_report"
    BASELINE_MODEL = "baseline_model"
    DEBIASED_MODEL = "debiased_model"
    VERIFICATION_REPORT = "verification_report"
    REPORT_JSON = "report_json"
    REPORT_MARKDOWN = "report_markdown"


class UploadStatus(str, Enum):
    INITIATED = "initiated"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionMode(str, Enum):
    SYNC = "sync"
    QUEUED = "queued"

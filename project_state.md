# Project State

## Status
The backend has been upgraded from request-coupled synchronous execution to an asynchronous, queue-oriented architecture that is still fully runnable in local development.

The main target of this pass was:
- async job submission
- decoupled orchestration
- pluggable storage with signed-URL-ready semantics
- a queue abstraction that can later move to Pub/Sub
- tests that verify the new execution model

All of that is implemented locally and covered by tests.

The previously detached `Model Training/` folder is now integrated through a dedicated workspace service and API routes for inspection, dataset generation, and audit regeneration.

## High-Level Architecture
FairLens now has two job representations:

1. In-memory async job state
- file: `app/services/job_store.py`
- stores `job_id`, `status`, `file_uri`, `config`, `result`, `error`, and timestamps
- powers `GET /api/v1/jobs/{job_id}`
- intentionally ephemeral and upgradeable later to Redis, Firestore, SQL, etc.

2. File-backed persisted audit record
- file: `app/services/repositories.py`
- stores the richer `AuditJobRecord` including artifact list, status history, and final `FairnessReport`
- powers report and artifact retrieval endpoints

This split lets the API poll a light async job object while keeping the existing persisted audit/report shape intact.

## Current Directory Structure
Generated directories such as `.venv`, `.pytest_cache`, and `__pycache__` omitted.

```text
.
├── Dockerfile
├── README.md
├── cloudbuild.yaml
├── project_state.md
├── pyproject.toml
├── app
│   ├── __init__.py
│   ├── adapters
│   │   ├── __init__.py
│   │   ├── compute.py
│   │   ├── queue.py
│   │   └── storage.py
│   ├── api
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── error_handlers.py
│   │   ├── router.py
│   │   └── routes
│   │       ├── __init__.py
│   │       ├── health.py
│   │       ├── hosted.py
│   │       ├── jobs.py
│   │       ├── metadata.py
│   │       ├── metrics.py
│   │       ├── model_training.py
│   │       └── uploads.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   └── security.py
│   ├── main.py
│   ├── ml
│   │   ├── __init__.py
│   │   ├── baseline.py
│   │   ├── counterfactual.py
│   │   ├── debiasing.py
│   │   ├── explainability.py
│   │   ├── features.py
│   │   ├── ingestion.py
│   │   ├── metrics.py
│   │   ├── pipeline.py
│   │   ├── scrubber.py
│   │   └── utils.py
│   ├── model_training
│   │   ├── __init__.py
│   │   ├── auditing.py
│   │   └── dataset_builder.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── domain.py
│   │   └── enums.py
│   ├── schemas
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── hosted.py
│   │   ├── jobs.py
│   │   ├── metrics.py
│   │   ├── model_training.py
│   │   ├── reports.py
│   │   └── uploads.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── artifact_service.py
│   │   ├── job_service.py
│   │   ├── job_store.py
│   │   ├── model_training_service.py
│   │   ├── orchestration.py
│   │   ├── reporting_service.py
│   │   ├── repositories.py
│   │   ├── runtime.py
│   │   └── upload_service.py
│   └── workers
│       ├── __init__.py
│       └── payloads.py
└── tests
    ├── conftest.py
    ├── test_api.py
    ├── test_config.py
    ├── test_job_store.py
    ├── test_metrics.py
    ├── test_model_training.py
    ├── test_pipeline.py
    └── test_storage_adapters.py
```

## Model Training Workspace
Files:
- `app/services/model_training_service.py`
- `app/model_training/auditing.py`
- `app/model_training/dataset_builder.py`
- `app/api/routes/model_training.py`

Purpose:
- Treat `Model Training/` as a configured workspace instead of importing loose scripts directly.
- Expose dependency-light steps through the backend:
  - workspace inspection
  - structured-to-unstructured dataset generation
  - fairness audit regeneration
- Keep heavy training steps optional behind the `ml` extra.

## What Is Now Async
These request paths no longer execute the ML pipeline inline:
- `POST /api/v1/jobs/debias`
- `POST /api/v1/jobs`
- `POST /api/v1/pipeline/execute`

The async path is:
1. API validates request.
2. `JobService.create_job()` creates:
   - an in-memory `AsyncJobRecord` with status `pending`
   - a persisted `AuditJobRecord` with status history
3. API schedules `JobService.enqueue_job()` as a FastAPI background task.
4. `JobOrchestrator.enqueue_job()` publishes a queue message.
5. `LocalQueueAdapter.publish_job()` spawns a background thread and invokes the registered handler.
6. `JobOrchestrator.run_job()` updates lifecycle state:
   - `pending -> running -> completed`
   - or `pending -> running -> failed`
7. Artifacts and report are persisted.
8. `GET /api/v1/jobs/{job_id}` exposes current state and final result summary.

## Queue Design
File: `app/adapters/queue.py`

Interface:
- `publish_job(payload)`
- `subscribe_jobs(handler)`

Implemented:
- `LocalQueueAdapter`
  - stores one subscriber handler
  - spawns a daemon thread per published job
  - calls the handler directly in development mode

Stubbed:
- `PubSubQueueAdapter`
  - preserves the adapter surface
  - returns topic metadata only
  - does not actually publish or consume Pub/Sub messages yet

Important wiring:
- `JobOrchestrator` registers itself as the queue subscriber in its constructor
- API routes know only enough to create a job and schedule enqueueing
- orchestration owns queue consumption and execution

## Storage Design
File: `app/adapters/storage.py`

Primary storage interface:
- `generate_upload_url()`
- `generate_download_url()`
- `save_file()`
- `get_file()`

Backward-compatible helpers still exist:
- `init_upload()`
- `complete_upload()`
- `artifact_exists()`
- `read_bytes()`
- `write_bytes()`
- `get_download_url()`
- `resolve_download_token()`

### Local Mode
Implemented fully.

Behavior:
- `POST /api/v1/uploads/init` returns:
  - `file_id`
  - `file_uri`
  - `upload_url`
  - `storage_mode`
- upload URLs are fake signed URLs of the form `/local-upload/{file_id}`
- uploaded bytes are stored under the configured local storage root
- download URLs are signed locally with HMAC and resolved by `GET /api/v1/downloads/{token}`

### GCS Mode
Scaffolded only.

Implemented:
- URI generation
- signed upload/download URL stub generation
- adapter shape and mode selection

Not implemented:
- direct cloud upload completion
- direct cloud file reads
- real signed URL calls through `google-cloud-storage`
- real artifact persistence to a bucket

Current intent:
- local mode is production-like for contract shape
- gcs mode preserves the interface so real cloud calls can be dropped in later

## Pipeline Decoupling
File: `app/ml/pipeline.py`

The pipeline remains FastAPI-free and filesystem-free.

New entrypoint:
- `FairLensPipeline.execute(request=PipelineRequest(...), data_loader=...)`

`PipelineRequest` contains:
- `job_id`
- `file_uri`
- `config`

The pipeline does not touch storage directly.
Instead:
- orchestration passes a loader callable
- the loader comes from `ArtifactService.load_dataframe`

Structured result exposed to async jobs:
- `metrics_before`
- `metrics_after`
- `summary`

The richer `FairnessReport` and model/data artifacts are still produced and persisted for downstream routes.

## Job Lifecycle
Statuses used by the async job store:
- `pending`
- `running`
- `completed`
- `failed`

Important files:
- `app/services/job_store.py`
- `app/services/job_service.py`
- `app/services/orchestration.py`

Important details:
- timestamps are updated on each state transition
- `started_at` is set when the job first moves to `running`
- `completed_at` is set on terminal states
- `error` stores the failure message
- `result` stores the pipeline summary payload returned by `PipelineRunOutput.to_job_result()`

## API Flow
### Upload Flow
1. `POST /api/v1/uploads/init`
2. client uploads to returned URL
3. upload returns `file_uri`
4. client uses `file_uri` when submitting a job

### Debias Flow
1. `POST /api/v1/jobs/debias`
2. API returns `202 Accepted` with `job_id` and `status_url`
3. client polls `GET /api/v1/jobs/{job_id}`
4. once completed, client can fetch:
   - `GET /api/v1/jobs/{job_id}/report`
   - `GET /api/v1/jobs/{job_id}/artifacts/{artifact_kind}`

### Inline Records Flow
`POST /api/v1/pipeline/execute` now behaves like an async submission helper:
- request records are written to local storage first
- a normal async job is created from that file
- the route returns `202 Accepted`

## Persistence Notes
File-backed repository behavior changed:
- writes are now atomic
- reads are lock-protected

Reason:
- background workers can read job files while the API thread is still persisting updates
- plain `write_text()` caused a race where a worker could observe an empty file

## Runtime Wiring
File: `app/services/runtime.py`

The application container now assembles:
- settings
- storage adapter
- queue adapter
- compute adapter
- in-memory job store
- file-backed repository
- artifact service
- upload service
- reporting service
- pipeline
- orchestrator
- job service

## Testing State
Tests now cover:
- `tests/test_job_store.py`
  - async job lifecycle transitions
- `tests/test_storage_adapters.py`
  - local mode round-trip
  - GCS stub URL generation
- `tests/test_pipeline.py`
  - pipeline execution from `file_uri + config`
- `tests/test_api.py`
  - full async API flow
  - async behavior under delayed pipeline execution
  - async inline-record execution

Command used:
```bash
./.venv/bin/pytest -q
```

Current result:
- all tests passing

## Implemented vs Stubbed
### Implemented
- async submission with `202 Accepted`
- background job enqueueing
- local queue worker dispatch
- in-memory async job store
- atomic persisted job record writes
- local upload/download contract flow
- local artifact persistence
- decoupled pipeline request shape
- job polling endpoint

### Stubbed / Future-Ready
- real Pub/Sub publish/consume
- real GCS signed upload URLs
- real GCS artifact reads/writes
- execution on Vertex AI
- durable async job store beyond process memory

## Modified / Created Files In This Pass
- `app/adapters/queue.py`
- `app/adapters/storage.py`
- `app/api/routes/jobs.py`
- `app/api/routes/metadata.py`
- `app/api/routes/uploads.py`
- `app/core/config.py`
- `app/main.py`
- `app/ml/pipeline.py`
- `app/models/domain.py`
- `app/models/enums.py`
- `app/schemas/jobs.py`
- `app/schemas/uploads.py`
- `app/services/job_service.py`
- `app/services/job_store.py`
- `app/services/orchestration.py`
- `app/services/repositories.py`
- `app/services/runtime.py`
- `app/workers/payloads.py`
- `tests/conftest.py`
- `tests/test_api.py`
- `tests/test_job_store.py`
- `tests/test_pipeline.py`
- `tests/test_storage_adapters.py`
- `README.md`
- `project_state.md`

## Run Instructions
```bash
python -m venv .venv
./.venv/bin/pip install -e .[dev]
./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## Test Instructions
```bash
./.venv/bin/pytest -q
```

## Next Steps
1. Replace `LocalQueueAdapter` with real Pub/Sub publisher and subscriber workers.
2. Replace GCS URL stubs in `app/adapters/storage.py` with `google-cloud-storage` signed URL generation and real blob reads/writes.
3. Move pipeline execution out of the API process entirely.
4. Use the queue payload as the handoff contract to a remote worker.
5. Replace the in-memory `InMemoryJobStore` with a durable shared store.
6. Move compute execution to Vertex AI and preserve current polling/report routes as the control plane.

---

## Recovered Pre-Async Snapshot
This section is appended intentionally to preserve earlier project-state context rather than replacing it.

Note:
- this snapshot is recovered from the earlier session-visible file contents
- it should be treated as historical context from before the async refactor
- it may be partial if some trailing lines were not recoverable from the current workspace

### Project Overview
FairLens is a Python-only backend for an ATS fairness auditing and remediation pipeline. The backend is built with FastAPI and implements the required `Audit, Fix, Verify` lifecycle from the uploaded FairLens specifications:
- secure upload initialization
- resume/dataset ingestion
- text scrubbing and proxy masking
- semantic feature extraction
- baseline fairness audit
- adversarial debiasing surrogate loop
- verification pass
- report and artifact persistence
- hosted scoring path

The repository started effectively empty and was built from scratch around the uploaded specifications:
- `/home/admin/Downloads/Comprehensive Technical Specification_ FairLens ATS Pipeline.pdf`
- `/home/admin/Downloads/FairLens_Technical_Design_Document.pdf`

### Current Goal
The current implementation goal was to build a complete, modular, production-minded backend from scratch, verify it locally, and document it well enough that a future Codex session can continue without additional user context.

That goal is complete for the current pass.

### Current Architecture
The backend is organized into six major layers:

1. API Layer
- FastAPI app in `app/main.py`
- route modules in `app/api/routes`
- centralized dependency wiring in `app/api/dependencies.py`
- centralized exception handling in `app/api/error_handlers.py`

2. Core Infrastructure
- settings via `pydantic-settings`
- logging setup
- shared exceptions
- hosted API key validation helper

3. Domain and Schema Contracts
- internal domain models in `app/models/domain.py`
- enums in `app/models/enums.py`
- external API request/response schemas in `app/schemas/*`

4. Adapter Layer
- local file-backed storage adapter
- GCS signed upload/download adapter
- local queue adapter and Pub/Sub hook
- local compute adapter and Vertex AI hook

5. Service Layer
- artifact persistence and retrieval
- upload orchestration
- job persistence and orchestration
- markdown report generation
- runtime container composition

6. ML / Fairness Layer
- dataset ingestion normalization
- resume scrubbing and proxy masking
- deterministic feature extraction
- NumPy logistic baseline predictor
- deterministic adversarial debiasing surrogate
- fairness metrics engine
- counterfactual audit
- SHAP-style explainability surrogate
- end-to-end pipeline orchestration

### Directory Structure
Source tree, excluding generated directories such as `.venv`, `.pytest_cache`, `__pycache__`, and editable install metadata:

```text
.
├── Dockerfile
├── README.md
├── cloudbuild.yaml
├── project_state.md
├── pyproject.toml
├── app
│   ├── __init__.py
│   ├── adapters
│   │   ├── __init__.py
│   │   ├── compute.py
│   │   ├── queue.py
│   │   └── storage.py
│   ├── api
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── error_handlers.py
│   │   ├── router.py
│   │   └── routes
│   │       ├── __init__.py
│   │       ├── health.py
│   │       ├── hosted.py
│   │       ├── jobs.py
│   │       ├── metadata.py
│   │       ├── metrics.py
│   │       └── uploads.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   └── security.py
│   ├── main.py
│   ├── ml
│   │   ├── __init__.py
│   │   ├── baseline.py
│   │   ├── counterfactual.py
│   │   ├── debiasing.py
│   │   ├── explainability.py
│   │   ├── features.py
│   │   ├── ingestion.py
│   │   ├── metrics.py
│   │   ├── pipeline.py
│   │   ├── scrubber.py
│   │   └── utils.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── domain.py
│   │   └── enums.py
│   ├── schemas
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── hosted.py
│   │   ├── jobs.py
│   │   ├── metrics.py
│   │   ├── reports.py
│   │   └── uploads.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── artifact_service.py
│   │   ├── job_service.py
│   │   ├── orchestration.py
│   │   ├── reporting_service.py
│   │   ├── repositories.py
│   │   ├── runtime.py
│   │   └── upload_service.py
│   └── workers
│       ├── __init__.py
│       └── payloads.py
└── tests
    ├── conftest.py
    ├── test_api.py
    ├── test_pipeline.py
    ├── test_storage_adapters.py
    ├── test_metrics.py
    └── test_config.py
```

### Implemented Files
Important files created or materially implemented:

- Root
  - `pyproject.toml`
  - `README.md`
  - `project_state.md`
  - `Dockerfile`
  - `cloudbuild.yaml`
  - `.env.example`
  - `.gitignore`

- API
  - `app/main.py`
  - `app/api/router.py`
  - `app/api/dependencies.py`
  - `app/api/error_handlers.py`
  - `app/api/routes/health.py`
  - `app/api/routes/metadata.py`
  - `app/api/routes/metrics.py`
  - `app/api/routes/uploads.py`
  - `app/api/routes/jobs.py`
  - `app/api/routes/hosted.py`

- Core
  - `app/core/config.py`
  - `app/core/logging.py`
  - `app/core/exceptions.py`
  - `app/core/security.py`

- Domain
  - `app/models/enums.py`
  - `app/models/domain.py`
  - `app/schemas/common.py`
  - `app/schemas/uploads.py`
  - `app/schemas/metrics.py`
  - `app/schemas/jobs.py`
  - `app/schemas/reports.py`
  - `app/schemas/hosted.py`

- Adapters
  - `app/adapters/storage.py`
  - `app/adapters/queue.py`
  - `app/adapters/compute.py`

- Services
  - `app/services/repositories.py`
  - `app/services/upload_service.py`
  - `app/services/artifact_service.py`
  - `app/services/reporting_service.py`
  - `app/services/orchestration.py`
  - `app/services/job_service.py`
  - `app/services/runtime.py`

- ML
  - `app/ml/ingestion.py`
  - `app/ml/scrubber.py`
  - `app/ml/features.py`
  - `app/ml/baseline.py`
  - `app/ml/debiasing.py`
  - `app/ml/metrics.py`
  - `app/ml/counterfactual.py`
  - `app/ml/explainability.py`
  - `app/ml/pipeline.py`
  - `app/ml/utils.py`

- Tests
  - `tests/conftest.py`
  - `tests/test_api.py`
  - `tests/test_pipeline.py`
  - `tests/test_storage_adapters.py`
  - `tests/test_metrics.py`
  - `tests/test_config.py`

### Implemented Features
Implemented backend capabilities:

- FastAPI service with `/api/v1` route namespace
- health and metadata endpoints
- metric catalog endpoint
- upload-init flow
- local upload-complete endpoint for development and tests
- file-backed local artifact storage
- signed local download URL flow using HMAC tokens
- GCS signed upload/download adapter hooks
- job creation, status tracking, and persistence
- full pipeline execution from uploaded CSV artifact
- inline pipeline execution endpoint
- fairness report retrieval endpoint
- artifact retrieval/download endpoint
- hosted scoring endpoint
- local queue and compute hook recording
- Pub/Sub and Vertex AI adapter entry points
- deterministic report generation in JSON and Markdown
- Docker container for Cloud Run deployment
- Cloud Build config for test + build flow

### Pipeline Flow
The implemented pipeline executes in this order:

1. Dataset Ingestion
- normalize column names
- validate label column
- validate protected attribute columns
- infer or validate the resume text column
- create internal `__resume_text` and `__label` fields

2. Baseline Feature Extraction
- build text-derived numeric features from raw resume text
- include protected-attribute one-hot features in baseline mode
- include numeric and low-cardinality categorical columns

3. Baseline Audit
- train a deterministic NumPy logistic predictor on a train split
- evaluate on a deterministic holdout split
- compute baseline fairness metrics

4. Scrubbing / Proxy Masking
- mask direct identifiers such as email, phone, URLs, years, and pronouns
- mask proxy concepts such as prestige, affinity, ethnicity, location, and gender-coded language
- create `__scrubbed_text`, mask counts, and proxy hit counts

5. Verification Feature Extraction
- build features from scrubbed text
- exclude protected attributes from the verification feature set

6. Adversarial Debiasing Surrogate
- fit a predictor on scrubbed features
- fit adversary classifiers to protected-group indicator targets
- aggregate adversary coefficient strength
- shrink predictor coefficients carrying strong demographic signal

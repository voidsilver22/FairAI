# FairAI: FairLens ATS Pipeline

FairAI is a comprehensive platform for auditing and remediating bias in Applicant Tracking Systems (ATS). It provides a full-stack solution including a FastAPI backend for asynchronous ML pipeline execution and a React frontend for exploring results and managing audits.

## Project Structure

```text
.
├── app/                # FastAPI Backend source code
├── frontend/           # React + TypeScript + Vite Frontend
├── ml/                 # ML Pipeline core logic
├── Model Training/     # Integrated model training workspace
├── tests/              # Backend test suite
├── project_state.md    # Detailed technical state (read first for devs)
└── pyproject.toml      # Backend dependencies and metadata
```

---

## Getting Started

### Backend Setup (FastAPI)

The backend uses a pluggable architecture (storage, queue, compute) ready for GCP but fully runnable locally.

1. **Environment Setup:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .\.venv\Scripts\activate
   pip install -e .[dev]
   ```

2. **Run Backend:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
   ```

3. **Run Tests:**
   ```bash
   pytest -q
   ```

**Important Environment Variables:**
- `FAIRLENS_LOCAL_STORAGE_ROOT=.fairlens-data`
- `FAIRLENS_QUEUE_BACKEND=local`
- `FAIRLENS_STORAGE_BACKEND=local`

### Frontend Setup (React)

The frontend is a modern React application built with Vite, Tailwind CSS, and TanStack Query.

1. **Install Dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Run Development Server:**
   ```bash
   npm run dev
   ```

---

## Backend Architecture

FairAI features an asynchronous job architecture designed for scalability:

- **Async Jobs:** Submission returns `202 Accepted`. Jobs run on background threads (local) or via Pub/Sub (cloud).
- **Pluggable Adapters:**
  - `storage.py`: Local filesystem or Google Cloud Storage.
  - `queue.py`: In-memory thread dispatcher or GCP Pub/Sub.
  - `compute.py`: Local execution or Vertex AI.
- **ML Pipeline:** Decoupled from the API, accepting `file_uri + config` for execution.

### Key Endpoints
- `POST /api/v1/uploads/init`: Initialize a file upload.
- `POST /api/v1/jobs/debias`: Submit a new debiasing job.
- `GET /api/v1/jobs/{job_id}`: Poll job status.
- `GET /api/v1/jobs/{job_id}/report`: Fetch the final fairness report.
- `POST /api/v1/model-training/audit`: Regenerate audit reports from existing data.

---

## Model Training Integration

The `Model Training/` folder is integrated as a workspace service.
- **Inspect:** `GET /api/v1/model-training` lists available training capabilities.
- **Dataset Generation:** `POST /api/v1/model-training/dataset` builds unstructured datasets from raw sources.
- **Auditing:** `POST /api/v1/model-training/audit` regenerates reports.

To enable full ML training capabilities, install the ML extras:
```bash
pip install -e .[ml]
```

---

## Local vs Cloud
- **Local:** Fully implemented for uploads, jobs, and artifact persistence.
- **Cloud (GCP):** Scaffolded with adapters for GCS, Pub/Sub, and Vertex AI. Signed URLs and URI generation are in place, ready for full cloud integration.

For a deeper dive into the technical implementation and recent changes, please refer to [project_state.md](./project_state.md).

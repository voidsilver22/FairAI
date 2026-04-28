from __future__ import annotations

from app.models.enums import JobStatus
from app.services.job_store import InMemoryJobStore


def test_job_store_tracks_job_lifecycle():
    store = InMemoryJobStore()
    job = store.create_job(
        job_id="job-1",
        file_uri="local://uploads/job-1.csv",
        config={"label_column": "hired"},
    )

    assert job.job_id == "job-1"
    assert job.status == JobStatus.PENDING
    assert job.started_at is None

    running = store.update_job("job-1", status=JobStatus.RUNNING)
    assert running.status == JobStatus.RUNNING
    assert running.started_at is not None

    completed = store.update_job(
        "job-1",
        status=JobStatus.COMPLETED,
        result={"summary": {"fairness_improvement": 0.12}},
    )
    assert completed.status == JobStatus.COMPLETED
    assert completed.result == {"summary": {"fairness_improvement": 0.12}}
    assert completed.completed_at is not None

    fetched = store.get_job("job-1")
    assert fetched.status == JobStatus.COMPLETED

from __future__ import annotations

import time

from app.services.runtime import get_application_container


def wait_for_terminal_job(api_client, status_url: str, timeout_seconds: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = api_client.get(status_url)
        assert response.status_code == 200
        payload = response.json()["job"]
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.05)
    raise AssertionError(f"Job did not reach a terminal state within {timeout_seconds} seconds.")


def upload_sample_file(api_client, sample_csv_bytes: bytes) -> str:
    init_response = api_client.post(
        "/api/v1/uploads/init",
        json={"filename": "resumes.csv", "content_type": "text/csv"},
    )
    assert init_response.status_code == 200
    upload_contract = init_response.json()
    assert upload_contract["storage_mode"] == "local"
    assert upload_contract["upload_url"].startswith("/local-upload/")

    upload_response = api_client.post(
        upload_contract["upload_url"],
        files={"file": ("resumes.csv", sample_csv_bytes, "text/csv")},
    )
    assert upload_response.status_code == 200
    return upload_response.json()["file_uri"]


def test_full_async_api_flow(api_client, sample_csv_bytes):
    file_uri = upload_sample_file(api_client, sample_csv_bytes)

    job_response = api_client.post(
        "/api/v1/jobs/debias",
        json={
            "file_uri": file_uri,
            "config": {
                "resume_text_column": "resume_text",
                "label_column": "hired",
                "positive_label": 1,
                "protected_attributes": ["gender"],
                "conditional_attributes": ["years_experience_bucket"],
            },
        },
    )
    assert job_response.status_code == 202
    job_payload = job_response.json()
    assert job_payload["status"] == "accepted"

    terminal_job = wait_for_terminal_job(api_client, job_payload["status_url"])
    assert terminal_job["status"] == "completed"
    assert terminal_job["result"]["summary"]["fairness_improvement"] >= -1.0

    report_response = api_client.get(f"/api/v1/jobs/{job_payload['job_id']}/report")
    assert report_response.status_code == 200
    report_payload = report_response.json()["report"]
    assert report_payload["summary"]["verification_metric_pass_rate"] >= 0.0

    artifact_response = api_client.get(
        f"/api/v1/jobs/{job_payload['job_id']}/artifacts/report_json"
    )
    assert artifact_response.status_code == 200
    artifact_payload = artifact_response.json()
    download_response = api_client.get(artifact_payload["download_url"])
    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith("application/json")

    hosted_response = api_client.post(
        "/api/v1/hosted/score",
        json={
            "job_id": job_payload["job_id"],
            "resume_text": "7 years experience Python SQL FastAPI machine learning leadership",
        },
    )
    assert hosted_response.status_code == 200
    hosted_payload = hosted_response.json()
    assert 0.0 <= hosted_payload["score"] <= 1.0


def test_pipeline_execute_endpoint_submits_async_job(api_client, sample_records):
    response = api_client.post(
        "/api/v1/pipeline/execute",
        json={
            "records": sample_records[:20],
            "resume_text_column": "resume_text",
            "label_column": "hired",
            "positive_label": 1,
            "protected_attributes": ["gender"],
        },
    )
    assert response.status_code == 202
    payload = response.json()
    terminal_job = wait_for_terminal_job(api_client, payload["status_url"])
    assert terminal_job["status"] == "completed"
    assert terminal_job["result"]["metrics_before"]["fairness"]


def test_job_submit_returns_before_pipeline_finishes(api_client, sample_csv_bytes, monkeypatch):
    file_uri = upload_sample_file(api_client, sample_csv_bytes)
    container = get_application_container()
    original_execute = container.pipeline.execute

    def delayed_execute(*args, **kwargs):
        time.sleep(0.35)
        return original_execute(*args, **kwargs)

    monkeypatch.setattr(container.pipeline, "execute", delayed_execute)

    started_at = time.monotonic()
    response = api_client.post(
        "/api/v1/jobs/debias",
        json={
            "file_uri": file_uri,
            "config": {
                "resume_text_column": "resume_text",
                "label_column": "hired",
                "positive_label": 1,
                "protected_attributes": ["gender"],
            },
        },
    )
    elapsed = time.monotonic() - started_at

    assert response.status_code == 202
    assert elapsed < 0.25

    status_payload = api_client.get(response.json()["status_url"]).json()["job"]
    assert status_payload["status"] in {"pending", "running"}
    terminal_job = wait_for_terminal_job(api_client, response.json()["status_url"])
    assert terminal_job["status"] == "completed"

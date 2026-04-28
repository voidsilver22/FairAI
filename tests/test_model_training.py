from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.core.config import reset_settings_cache
from app.main import create_app
from app.services.runtime import reset_application_container
from conftest import AsgiClient


def _build_api_client(tmp_path: Path, workspace: Path, monkeypatch) -> AsgiClient:
    monkeypatch.setenv("FAIRLENS_ENVIRONMENT", "test")
    monkeypatch.setenv("FAIRLENS_STORAGE_BACKEND", "local")
    monkeypatch.setenv("FAIRLENS_QUEUE_BACKEND", "local")
    monkeypatch.setenv("FAIRLENS_COMPUTE_BACKEND", "local")
    monkeypatch.setenv("FAIRLENS_EXECUTE_INLINE_JOBS", "true")
    monkeypatch.setenv("FAIRLENS_SIGNED_URL_SECRET", "test-secret")
    monkeypatch.setenv("FAIRLENS_LOCAL_STORAGE_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("FAIRLENS_MAX_COUNTERFACTUAL_SAMPLES", "32")
    monkeypatch.setenv("FAIRLENS_MODEL_TRAINING_WORKSPACE", str(workspace))
    reset_settings_cache()
    reset_application_container()
    return AsgiClient(create_app())


def test_model_training_workspace_and_dataset_build(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "Model Training"
    workspace.mkdir(parents=True, exist_ok=True)
    structured = pd.DataFrame(
        [
            {
                "career_objective": "Seeking a data role.",
                "positions": "Data Analyst",
                "professional_company_names": "Acme Corp",
                "degree_names": "B.Tech",
                "major_field_of_studies": "Computer Science",
                "educational_institution_name": "State University",
                "passing_years": "2022",
                "skills": "Python, SQL, Tableau",
                "certification_skills": "AWS",
                "languages": "English",
                "gender": "Female",
                "age_group": "21-26",
                "college_tier": "Tier 3",
                "region": "Metro",
                "protected_group": "Female_Tier 3_Metro",
                "matched_score": 0.82,
                "shortlisted": 1,
            },
            {
                "career_objective": "Looking for backend engineering work.",
                "positions": "Backend Engineer",
                "professional_company_names": "Beta Systems",
                "degree_names": "B.E.",
                "major_field_of_studies": "Information Technology",
                "educational_institution_name": "Tech Institute",
                "passing_years": "2020",
                "skills": "FastAPI, PostgreSQL, Docker",
                "certification_skills": "GCP",
                "languages": "English, Hindi",
                "gender": "Male",
                "age_group": "35-44",
                "college_tier": "Tier 1",
                "region": "Non-Metro",
                "protected_group": "Male_Tier 1_Non-Metro",
                "matched_score": 0.91,
                "shortlisted": 1,
            },
        ]
    )
    structured.to_csv(workspace / "fairlens_dataset_structured.csv", index=False)

    client = _build_api_client(tmp_path, workspace, monkeypatch)

    summary_response = client.get("/api/v1/model-training")
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["exists"] is True
    assert any(file["name"] == "fairlens_dataset_structured.csv" for file in summary_payload["files"])

    build_response = client.post("/api/v1/model-training/dataset", json={})
    assert build_response.status_code == 200
    build_payload = build_response.json()
    assert build_payload["row_count"] == 2
    assert build_payload["columns"][0] == "Raw_Resume_Text"

    output_frame = pd.read_csv(build_payload["output_path"])
    assert "Raw_Resume_Text" in output_frame.columns
    assert output_frame.loc[0, "Raw_Resume_Text"]


def test_model_training_audit_route_writes_report(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "Model Training"
    workspace.mkdir(parents=True, exist_ok=True)

    baseline_frame = pd.DataFrame(
        [
            {
                "Raw_Resume_Text": "candidate-1",
                "gender": "Male",
                "age_group": "35-44",
                "college_tier": "Tier 1",
                "region": "Non-Metro",
                "protected_group": "Male_Tier 1_Non-Metro",
                "matched_score": 0.90,
                "Model_Predicted_Score": 0.92,
            },
            {
                "Raw_Resume_Text": "candidate-2",
                "gender": "Male",
                "age_group": "35-44",
                "college_tier": "Tier 2",
                "region": "Non-Metro",
                "protected_group": "Male_Tier 2_Non-Metro",
                "matched_score": 0.82,
                "Model_Predicted_Score": 0.84,
            },
            {
                "Raw_Resume_Text": "candidate-3",
                "gender": "Female",
                "age_group": "21-26",
                "college_tier": "Tier 3",
                "region": "Metro",
                "protected_group": "Female_Tier 3_Metro",
                "matched_score": 0.88,
                "Model_Predicted_Score": 0.45,
            },
            {
                "Raw_Resume_Text": "candidate-4",
                "gender": "Female",
                "age_group": "21-26",
                "college_tier": "Tier 3",
                "region": "Metro",
                "protected_group": "Female_Tier 3_Metro",
                "matched_score": 0.20,
                "Model_Predicted_Score": 0.22,
            },
        ]
    )
    fairlens_frame = baseline_frame.rename(
        columns={"Model_Predicted_Score": "FairLens_Predicted_Score"}
    ).copy()
    fairlens_frame["FairLens_Predicted_Score"] = [0.88, 0.81, 0.79, 0.18]

    baseline_frame.to_csv(workspace / "baseline_scored_results.csv", index=False)
    fairlens_frame.to_csv(workspace / "clean_scored_results.csv", index=False)

    client = _build_api_client(tmp_path, workspace, monkeypatch)

    audit_response = client.post("/api/v1/model-training/audit", json={})
    assert audit_response.status_code == 200
    payload = audit_response.json()
    assert set(payload["report"].keys()) == {"Baseline", "FairLens"}
    assert "gender" in payload["report"]["Baseline"]
    assert (workspace / "final_audit_report.json").exists()

    persisted_report = json.loads((workspace / "final_audit_report.json").read_text(encoding="utf-8"))
    assert set(persisted_report.keys()) == {"Baseline", "FairLens"}

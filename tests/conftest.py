from __future__ import annotations

import csv
import io
import os
from pathlib import Path
import asyncio

import pytest
import httpx

from app.core.config import reset_settings_cache
from app.main import create_app
from app.services.runtime import reset_application_container


def build_biased_records(total_rows: int = 120) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for index in range(total_rows):
        gender = "male" if index % 2 == 0 else "female"
        strong_candidate = index % 4 in (0, 1)
        years_experience = 7 if strong_candidate else 2
        assessment_score = 88 if strong_candidate else 43
        skills = (
            "Python SQL FastAPI machine learning analytics leadership"
            if strong_candidate
            else "communication office excel support"
        )
        proxy = (
            "Harvard men's coding fraternity"
            if gender == "male"
            else "Wellesley women's engineering society"
        )
        hired = 1 if strong_candidate else 0
        if gender == "female" and strong_candidate and index % 8 == 1:
            hired = 0
        if gender == "male" and not strong_candidate and index % 8 == 0:
            hired = 1

        records.append(
            {
                "candidate_id": index,
                "resume_text": (
                    f"{years_experience} years experience. {skills}. "
                    f"Volunteer work with {proxy}."
                ),
                "gender": gender,
                "assessment_score": assessment_score,
                "hired": hired,
            }
        )
    return records


def build_csv_bytes(records: list[dict[str, object]]) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(records[0].keys()))
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue().encode("utf-8")


@pytest.fixture()
def sample_records() -> list[dict[str, object]]:
    return build_biased_records()


@pytest.fixture()
def sample_csv_bytes(sample_records: list[dict[str, object]]) -> bytes:
    return build_csv_bytes(sample_records)


@pytest.fixture()
def api_client(tmp_path: Path) -> AsgiClient:
    env = os.environ.copy()
    env["FAIRLENS_ENVIRONMENT"] = "test"
    env["FAIRLENS_STORAGE_BACKEND"] = "local"
    env["FAIRLENS_QUEUE_BACKEND"] = "local"
    env["FAIRLENS_COMPUTE_BACKEND"] = "local"
    env["FAIRLENS_EXECUTE_INLINE_JOBS"] = "true"
    env["FAIRLENS_SIGNED_URL_SECRET"] = "test-secret"
    env["FAIRLENS_LOCAL_STORAGE_ROOT"] = str(tmp_path / "runtime")
    env["FAIRLENS_MAX_COUNTERFACTUAL_SAMPLES"] = "32"
    os.environ.update(env)
    reset_settings_cache()
    reset_application_container()
    app = create_app()
    client = AsgiClient(app)
    try:
        yield client
    finally:
        reset_settings_cache()
        reset_application_container()
class AsgiClient:
    def __init__(self, app, base_url: str = "http://testserver") -> None:
        self.app = app
        self.base_url = base_url

    def get(self, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
        return asyncio.run(self.request("GET", url, headers=headers))

    def post(
        self,
        url: str,
        *,
        json: dict | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        return asyncio.run(
            self.request("POST", url, json=json, files=files, headers=headers)
        )

    async def request(
        self,
        method: str,
        url: str,
        *,
        json: dict | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url=self.base_url,
            headers=headers,
        ) as client:
            return await client.request(method, url, json=json, files=files)

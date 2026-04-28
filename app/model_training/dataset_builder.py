from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


REQUIRED_SOURCE_COLUMNS: tuple[str, ...] = (
    "career_objective",
    "positions",
    "professional_company_names",
    "degree_names",
    "major_field_of_studies",
    "educational_institution_name",
    "passing_years",
    "skills",
    "certification_skills",
    "languages",
)

OUTPUT_COLUMNS: tuple[str, ...] = (
    "Raw_Resume_Text",
    "gender",
    "age_group",
    "college_tier",
    "region",
    "protected_group",
    "matched_score",
    "shortlisted",
)


@dataclass(frozen=True, slots=True)
class UnstructuredDatasetBuildResult:
    input_path: Path
    output_path: Path
    row_count: int
    columns: list[str]


def build_messy_resume(row: pd.Series) -> str:
    templates = [
        (
            f"{row['career_objective']} Previously, I worked as a {row['positions']} "
            f"at {row['professional_company_names']}. I hold a {row['degree_names']} in "
            f"{row['major_field_of_studies']} from {row['educational_institution_name']}, "
            f"graduating in {row['passing_years']}. My technical toolkit includes "
            f"{row['skills']} and I have certifications in {row['certification_skills']}. "
            f"I am fluent in {row['languages']}."
        ),
        (
            f"Role: {row['positions']} @ {row['professional_company_names']}. "
            f"{row['career_objective']} Graduated {row['passing_years']} from "
            f"{row['educational_institution_name']} ({row['degree_names']} - "
            f"{row['major_field_of_studies']}). Proficiencies: {row['skills']}. "
            f"Extra certs: {row['certification_skills']}. Languages: {row['languages']}."
        ),
        (
            f"Alumni of {row['educational_institution_name']} ({row['passing_years']}) "
            f"with a {row['degree_names']} in {row['major_field_of_studies']}. Expert in "
            f"{row['skills']}. Certified in {row['certification_skills']}. Professional "
            f"background includes time at {row['professional_company_names']} as a "
            f"{row['positions']}. {row['career_objective']} Languages spoken: "
            f"{row['languages']}."
        ),
    ]
    template_index = int(row.name) % len(templates) if row.name is not None else 0
    return templates[template_index]


def build_unstructured_dataset(
    input_path: Path,
    output_path: Path,
) -> UnstructuredDatasetBuildResult:
    frame = pd.read_csv(input_path).fillna("")

    missing_columns = [
        column
        for column in [*REQUIRED_SOURCE_COLUMNS, *OUTPUT_COLUMNS[1:]]
        if column not in frame.columns
    ]
    if missing_columns:
        raise ValueError(
            "Structured dataset is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    generated = frame.copy()
    generated["Raw_Resume_Text"] = generated.apply(build_messy_resume, axis=1)
    pipeline_ready = generated.loc[:, OUTPUT_COLUMNS]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline_ready.to_csv(output_path, index=False)

    return UnstructuredDatasetBuildResult(
        input_path=input_path,
        output_path=output_path,
        row_count=len(pipeline_ready),
        columns=list(pipeline_ready.columns),
    )

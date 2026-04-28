from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.core.exceptions import FairLensError
from app.models.domain import AuditInputSpec, DatasetProfile


@dataclass(slots=True)
class PreparedDataset:
    frame: pd.DataFrame
    profile: DatasetProfile


class DatasetIngestor:
    """Normalize incoming dataset frames into a pipeline-friendly structure."""

    def prepare(self, frame: pd.DataFrame, spec: AuditInputSpec) -> PreparedDataset:
        if frame.empty:
            raise FairLensError("The input dataset is empty.", code="empty_dataset")

        prepared = frame.copy()
        prepared.columns = [str(column).strip() for column in prepared.columns]

        if spec.label_column not in prepared.columns:
            raise FairLensError(
                f"Label column '{spec.label_column}' is missing from the dataset.",
                code="missing_label_column",
            )

        missing_protected = [
            column
            for column in spec.protected_attributes
            if column not in prepared.columns
        ]
        if missing_protected:
            raise FairLensError(
                f"Protected attribute columns are missing: {missing_protected}",
                code="missing_protected_attributes",
            )

        resume_text_column = self._resolve_resume_text_column(prepared, spec)
        prepared["__resume_text"] = (
            prepared[resume_text_column].fillna("").astype(str).str.strip()
        )
        prepared["__label"] = (
            prepared[spec.label_column].astype(str)
            == str(spec.positive_label)
        ).astype(int)

        for column in spec.protected_attributes:
            prepared[column] = prepared[column].fillna("unknown").astype(str)

        profile = DatasetProfile(
            row_count=int(len(prepared)),
            column_count=int(len(prepared.columns)),
            columns=list(prepared.columns),
            resume_text_column=resume_text_column,
            protected_attribute_values={
                column: sorted(prepared[column].astype(str).unique().tolist())
                for column in spec.protected_attributes
            },
            positive_rate=round(float(prepared["__label"].mean()), 4),
        )
        return PreparedDataset(frame=prepared, profile=profile)

    def _resolve_resume_text_column(
        self,
        frame: pd.DataFrame,
        spec: AuditInputSpec,
    ) -> str:
        if spec.resume_text_column:
            if spec.resume_text_column not in frame.columns:
                raise FairLensError(
                    f"Resume text column '{spec.resume_text_column}' is missing.",
                    code="missing_resume_text_column",
                )
            return spec.resume_text_column

        candidates = [
            column
            for column in frame.columns
            if column.lower() in {"resume_text", "resume", "text", "content"}
        ]
        if candidates:
            return candidates[0]

        object_columns = [
            column
            for column in frame.columns
            if column not in {spec.label_column, *spec.protected_attributes}
            and frame[column].dtype == object
        ]
        if object_columns:
            generated_column = "__generated_resume_text"
            frame[generated_column] = (
                frame[object_columns]
                .fillna("")
                .astype(str)
                .agg(" ".join, axis=1)
                .str.strip()
            )
            return generated_column

        raise FairLensError(
            "No resume text column could be inferred from the dataset.",
            code="no_resume_text_column",
        )


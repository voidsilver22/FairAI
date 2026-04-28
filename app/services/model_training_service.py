from __future__ import annotations

import json
from importlib.util import find_spec
from pathlib import Path

from app.core.config import Settings
from app.core.exceptions import InvalidStateError, NotFoundError
from app.model_training import build_unstructured_dataset, generate_workspace_audit_report


class ModelTrainingService:
    _WORKSPACE_FILES: tuple[tuple[str, str, str], ...] = (
        ("structured_dataset", "fairlens_dataset_structured.csv", "dataset"),
        ("unstructured_dataset", "fairlens_dataset_unstructured.csv", "dataset"),
        ("baseline_model", "biased_baseline_ats.pkl", "model"),
        ("baseline_scores", "baseline_scored_results.csv", "results"),
        ("debiased_model", "fairlens_clean_model.pth", "model"),
        ("debiased_scores", "clean_scored_results.csv", "results"),
        ("final_audit_report", "final_audit_report.json", "report"),
        ("comparison_report", "comparison_report.json", "report"),
        ("consolidated_report", "fairlens_consolidated_report.json", "report"),
        ("baseline_reference_model", "baseline_model/biased_baseline_ats.pkl", "reference"),
        ("baseline_reference_scores", "baseline_model/baseline_full_predictions.csv", "reference"),
        ("baseline_reference_report", "baseline_model/baseline_bias_report.json", "reference"),
    )

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def workspace(self) -> Path:
        return self.settings.resolved_model_training_workspace()

    def describe_workspace(self) -> dict:
        workspace = self.workspace
        report_models: list[str] = []
        report_path = workspace / "final_audit_report.json"
        if report_path.exists():
            try:
                report_payload = json.loads(report_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                report_payload = {}
            if isinstance(report_payload, dict):
                report_models = list(report_payload.keys())

        notes = [
            "Workspace-backed integration wraps the existing Model Training assets without importing scripts from a path with spaces.",
            "Dataset build and audit generation run on core app dependencies. Heavy model training still requires the optional ml extras.",
        ]
        if not workspace.exists():
            notes.insert(0, "Configured model training workspace does not exist yet.")

        return {
            "workspace_path": str(workspace),
            "exists": workspace.exists(),
            "capabilities": self._capabilities(),
            "files": [self._describe_file(*entry) for entry in self._WORKSPACE_FILES],
            "generated_report_available": report_path.exists(),
            "report_models": report_models,
            "notes": notes,
        }

    def build_unstructured_dataset(
        self,
        *,
        input_filename: str = "fairlens_dataset_structured.csv",
        output_filename: str = "fairlens_dataset_unstructured.csv",
    ) -> dict:
        input_path = self.workspace / input_filename
        if not input_path.exists():
            raise NotFoundError(f"Structured dataset '{input_filename}' was not found in the model training workspace.")

        output_path = self.workspace / output_filename
        try:
            result = build_unstructured_dataset(input_path, output_path)
        except ValueError as error:
            raise InvalidStateError(str(error)) from error

        return {
            "input_path": str(result.input_path),
            "output_path": str(result.output_path),
            "row_count": result.row_count,
            "columns": result.columns,
        }

    def run_workspace_audit(
        self,
        *,
        baseline_results_filename: str = "baseline_scored_results.csv",
        fairlens_results_filename: str = "clean_scored_results.csv",
        baseline_score_column: str = "Model_Predicted_Score",
        fairlens_score_column: str = "FairLens_Predicted_Score",
        baseline_threshold: float = 0.70,
        fairlens_threshold: float = 0.685,
        output_filename: str = "final_audit_report.json",
    ) -> dict:
        baseline_path = self.workspace / baseline_results_filename
        fairlens_path = self.workspace / fairlens_results_filename
        missing_inputs = [
            filename
            for filename, path in (
                (baseline_results_filename, baseline_path),
                (fairlens_results_filename, fairlens_path),
            )
            if not path.exists()
        ]
        if missing_inputs:
            raise NotFoundError(
                "Model training audit inputs were not found: " + ", ".join(missing_inputs)
            )

        output_path = self.workspace / output_filename
        try:
            report = generate_workspace_audit_report(
                baseline_csv_path=baseline_path,
                fairlens_csv_path=fairlens_path,
                baseline_score_col=baseline_score_column,
                fairlens_score_col=fairlens_score_column,
                baseline_threshold=baseline_threshold,
                fairlens_threshold=fairlens_threshold,
                output_json_path=output_path,
            )
        except ValueError as error:
            raise InvalidStateError(str(error)) from error

        return {
            "output_path": str(output_path),
            "report": report,
        }

    def _describe_file(self, key: str, relative_path: str, category: str) -> dict:
        path = self.workspace / relative_path
        return {
            "key": key,
            "name": path.name,
            "path": str(path),
            "category": category,
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        }

    @staticmethod
    def _capabilities() -> dict[str, bool]:
        has_sentence_transformers = find_spec("sentence_transformers") is not None
        has_sklearn = find_spec("sklearn") is not None
        has_torch = find_spec("torch") is not None
        has_joblib = find_spec("joblib") is not None

        return {
            "build_unstructured_dataset": True,
            "generate_audit_report": True,
            "train_baseline_model": has_sentence_transformers and has_sklearn and has_joblib,
            "train_debiased_model": has_sentence_transformers and has_torch,
            "generate_fair_scores": has_sentence_transformers and has_torch,
        }

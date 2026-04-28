from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

from app.ml.baseline import LinearModelState, LinearModelTrainer
from app.ml.counterfactual import run_counterfactual_audit
from app.ml.debiasing import AdversarialDebiaser
from app.ml.explainability import ExplainabilityService
from app.ml.features import FeatureExtractor
from app.ml.ingestion import DatasetIngestor
from app.ml.metrics import FairnessMetricsEngine
from app.ml.scrubber import ResumeScrubber
from app.ml.utils import deterministic_test_mask, utc_now
from app.models.domain import (
    AuditInputSpec,
    FairnessReport,
    LinearModelArtifact,
)
from app.models.enums import PipelineStage


@dataclass(slots=True)
class PipelineArtifacts:
    scrubbed_frame: pd.DataFrame
    verification_feature_frame: pd.DataFrame
    baseline_model: LinearModelArtifact
    debiased_model: LinearModelArtifact


@dataclass(slots=True)
class PipelineRequest:
    job_id: str | None
    file_uri: str
    config: AuditInputSpec


@dataclass(slots=True)
class PipelineRunOutput:
    report: FairnessReport
    artifacts: PipelineArtifacts

    def to_job_result(self) -> dict[str, Any]:
        return {
            "metrics_before": {
                "performance": self.report.baseline_performance.model_dump(mode="json"),
                "fairness": [
                    metric.model_dump(mode="json") for metric in self.report.baseline_metrics
                ],
            },
            "metrics_after": {
                "performance": self.report.verification_performance.model_dump(mode="json"),
                "fairness": [
                    metric.model_dump(mode="json") for metric in self.report.verification_metrics
                ],
            },
            "summary": self.report.summary,
        }


class FairLensPipeline:
    def __init__(
        self,
        *,
        counterfactual_sample_size: int = 128,
    ) -> None:
        self.counterfactual_sample_size = counterfactual_sample_size
        self.ingestor = DatasetIngestor()
        self.scrubber = ResumeScrubber()
        self.feature_extractor = FeatureExtractor()
        self.trainer = LinearModelTrainer()
        self.debiaser = AdversarialDebiaser(self.trainer)
        self.metrics_engine = FairnessMetricsEngine()
        self.explainability = ExplainabilityService()

    def execute(
        self,
        *,
        request: PipelineRequest,
        data_loader: Callable[[str], pd.DataFrame],
        progress_callback: Callable[[PipelineStage, str], None] | None = None,
    ) -> PipelineRunOutput:
        frame = data_loader(request.file_uri)
        return self.run(
            job_id=request.job_id or request.file_uri,
            frame=frame,
            spec=request.config,
            progress_callback=progress_callback,
        )

    def run(
        self,
        *,
        job_id: str,
        frame: pd.DataFrame,
        spec: AuditInputSpec,
        progress_callback: Callable[[PipelineStage, str], None] | None = None,
    ) -> PipelineRunOutput:
        self._notify(progress_callback, PipelineStage.INGESTION, "Preparing dataset.")
        prepared = self.ingestor.prepare(frame, spec)
        normalized = prepared.frame
        labels = normalized["__label"].to_numpy(dtype=int)
        test_mask = deterministic_test_mask(len(normalized))
        train_mask = ~test_mask

        self._notify(progress_callback, PipelineStage.FEATURE_EXTRACTION, "Extracting baseline features.")
        raw_features_result = self.feature_extractor.build_features(
            normalized,
            text_column="__resume_text",
            label_column=spec.label_column,
            protected_attributes=spec.protected_attributes,
            include_protected_attributes=True,
        )
        self._notify(progress_callback, PipelineStage.BASELINE_AUDIT, "Training baseline predictor and computing baseline audit.")
        baseline_train_features = raw_features_result.features.loc[train_mask]
        baseline_test_features = raw_features_result.features.loc[test_mask]
        baseline_model = self.trainer.fit_dataframe(
            baseline_train_features,
            labels[train_mask],
            model_name="baseline_predictor",
        )
        baseline_bundle = self.trainer.evaluate(
            baseline_model,
            baseline_test_features,
            labels[test_mask],
        )

        self._notify(progress_callback, PipelineStage.SCRUBBING, "Scrubbing direct and proxy identifiers.")
        scrubbed = self.scrubber.scrub_frame(normalized, "__resume_text")
        self._notify(progress_callback, PipelineStage.FEATURE_EXTRACTION, "Extracting scrubbed semantic features.")
        scrubbed_features_result = self.feature_extractor.build_features(
            scrubbed.frame,
            text_column="__scrubbed_text",
            label_column=spec.label_column,
            protected_attributes=spec.protected_attributes,
            include_protected_attributes=False,
        )
        self._notify(progress_callback, PipelineStage.DEBIASING, "Running adversarial debiasing surrogate.")
        debiasing = self.debiaser.fit(
            scrubbed_features_result.features,
            labels,
            scrubbed_features_result.annotated_frame[spec.protected_attributes],
            train_mask,
            test_mask,
            fairness_weight=spec.fairness_weight,
        )

        self._notify(progress_callback, PipelineStage.VERIFICATION, "Running counterfactual and fairness verification passes.")
        baseline_counterfactuals = self._counterfactual_suite(
            stage="baseline",
            frame=normalized.loc[test_mask].reset_index(drop=True),
            protected_attributes=spec.protected_attributes,
            scorer=self._make_baseline_scorer(baseline_model, spec),
        )
        verification_counterfactuals = self._counterfactual_suite(
            stage="verification",
            frame=scrubbed.frame.loc[test_mask].reset_index(drop=True),
            protected_attributes=spec.protected_attributes,
            scorer=self._make_verification_scorer(debiasing.model, spec),
        )

        feature_attributions = self.explainability.build_feature_attributions(
            baseline_model=baseline_model,
            verification_model=debiasing.model,
            baseline_feature_frame=raw_features_result.features.loc[test_mask],
            verification_feature_frame=scrubbed_features_result.features.loc[test_mask],
            protected_frame=scrubbed_features_result.annotated_frame.loc[test_mask, spec.protected_attributes],
        )

        baseline_metrics = self.metrics_engine.compute_group_metrics(
            evaluation_frame=raw_features_result.annotated_frame.loc[test_mask],
            labels=labels[test_mask],
            predictions=baseline_bundle.predictions,
            stage="baseline",
            protected_attributes=spec.protected_attributes,
            conditional_attributes=spec.conditional_attributes,
            counterfactuals=baseline_counterfactuals,
            feature_attributions=feature_attributions,
            metadata=spec.metadata,
        )
        verification_metrics = self.metrics_engine.compute_group_metrics(
            evaluation_frame=scrubbed_features_result.annotated_frame.loc[test_mask],
            labels=labels[test_mask],
            predictions=debiasing.prediction_bundle.predictions,
            stage="verification",
            protected_attributes=spec.protected_attributes,
            conditional_attributes=spec.conditional_attributes,
            counterfactuals=verification_counterfactuals,
            feature_attributions=feature_attributions,
            metadata=spec.metadata,
        )

        report = FairnessReport(
            job_id=job_id,
            created_at=utc_now(),
            dataset_profile=prepared.profile,
            baseline_performance=baseline_bundle.performance,
            verification_performance=debiasing.prediction_bundle.performance,
            baseline_metrics=baseline_metrics,
            verification_metrics=verification_metrics,
            counterfactuals=[*baseline_counterfactuals, *verification_counterfactuals],
            feature_attributions=feature_attributions,
            remediation=debiasing.remediation,
            summary=self._build_summary(
                baseline_metrics=baseline_metrics,
                verification_metrics=verification_metrics,
                baseline_accuracy=baseline_bundle.performance.accuracy,
                verification_accuracy=debiasing.prediction_bundle.performance.accuracy,
            ),
        )
        self._notify(progress_callback, PipelineStage.REPORTING, "Finalizing report artifacts.")

        return PipelineRunOutput(
            report=report,
            artifacts=PipelineArtifacts(
                scrubbed_frame=scrubbed.frame,
                verification_feature_frame=scrubbed_features_result.features,
                baseline_model=baseline_model.to_artifact(),
                debiased_model=debiasing.model.to_artifact(),
            ),
        )

    @staticmethod
    def _notify(
        progress_callback: Callable[[PipelineStage, str], None] | None,
        stage: PipelineStage,
        message: str,
    ) -> None:
        if progress_callback is not None:
            progress_callback(stage, message)

    def _make_baseline_scorer(
        self,
        model: LinearModelState,
        spec: AuditInputSpec,
    ) -> Callable[[pd.DataFrame], list[int]]:
        def score(frame: pd.DataFrame) -> list[int]:
            result = self.feature_extractor.build_features(
                frame,
                text_column="__resume_text",
                label_column=spec.label_column,
                protected_attributes=spec.protected_attributes,
                include_protected_attributes=True,
            )
            predictions = model.predict_binary(result.features)
            return predictions.astype(int).tolist()

        return score

    def _make_verification_scorer(
        self,
        model: LinearModelState,
        spec: AuditInputSpec,
    ) -> Callable[[pd.DataFrame], list[int]]:
        def score(frame: pd.DataFrame) -> list[int]:
            working = frame.copy()
            if "__scrubbed_text" not in working.columns:
                scrubbed = self.scrubber.scrub_frame(working, "__resume_text")
                working = scrubbed.frame
            result = self.feature_extractor.build_features(
                working,
                text_column="__scrubbed_text",
                label_column=spec.label_column,
                protected_attributes=spec.protected_attributes,
                include_protected_attributes=False,
            )
            predictions = model.predict_binary(result.features)
            return predictions.astype(int).tolist()

        return score

    def _counterfactual_suite(
        self,
        *,
        stage: str,
        frame: pd.DataFrame,
        protected_attributes: list[str],
        scorer: Callable[[pd.DataFrame], list[int]],
    ) -> list:
        results = []
        for protected_attribute in protected_attributes:
            results.append(
                run_counterfactual_audit(
                    frame,
                    protected_attribute=protected_attribute,
                    score_callable=scorer,
                    stage=stage,
                    n_samples=self.counterfactual_sample_size,
                )
            )
        return results

    def _build_summary(
        self,
        *,
        baseline_metrics: list,
        verification_metrics: list,
        baseline_accuracy: float,
        verification_accuracy: float,
    ) -> dict[str, float]:
        baseline_pass_rate = (
            sum(metric.passed for metric in baseline_metrics) / max(len(baseline_metrics), 1)
        )
        verification_pass_rate = (
            sum(metric.passed for metric in verification_metrics) / max(len(verification_metrics), 1)
        )
        return {
            "baseline_metric_pass_rate": round(float(baseline_pass_rate), 4),
            "verification_metric_pass_rate": round(float(verification_pass_rate), 4),
            "fairness_improvement": round(float(verification_pass_rate - baseline_pass_rate), 4),
            "accuracy_delta": round(float(verification_accuracy - baseline_accuracy), 4),
        }

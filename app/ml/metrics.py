from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from app.ml.utils import safe_divide
from app.models.domain import CounterfactualAudit, FeatureAttribution, MetricResult
from app.models.enums import Severity
from app.schemas.metrics import MetricDefinitionResponse


Comparator = Literal["gte", "abs_lte", "between"]


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    key: str
    name: str
    description: str
    threshold: float
    comparator: Comparator
    regulation_refs: tuple[str, ...]
    implementation_status: str
    notes: str | None = None
    lower_threshold: float | None = None


METRIC_CATALOG: dict[str, MetricDefinition] = {
    "disparate_impact": MetricDefinition(
        key="disparate_impact",
        name="Disparate Impact (4/5ths Rule)",
        description="Selection-rate ratio between comparison groups.",
        threshold=0.8,
        comparator="gte",
        regulation_refs=("EEOC 4/5ths Rule", "GDPR Art.22"),
        implementation_status="full",
    ),
    "demographic_parity_difference": MetricDefinition(
        key="demographic_parity_difference",
        name="Demographic Parity Difference",
        description="Absolute selection-rate difference between groups.",
        threshold=0.1,
        comparator="abs_lte",
        regulation_refs=("EU AI Act", "Fairlearn parity guidance"),
        implementation_status="full",
    ),
    "equal_opportunity_difference": MetricDefinition(
        key="equal_opportunity_difference",
        name="Equal Opportunity Difference",
        description="True-positive-rate difference between groups.",
        threshold=0.1,
        comparator="abs_lte",
        regulation_refs=("Hardt et al. 2016",),
        implementation_status="full",
    ),
    "average_odds_difference": MetricDefinition(
        key="average_odds_difference",
        name="Average Odds Difference",
        description="Average of TPR and FPR differences.",
        threshold=0.1,
        comparator="abs_lte",
        regulation_refs=("Hardt et al. 2016",),
        implementation_status="full",
    ),
    "predictive_parity": MetricDefinition(
        key="predictive_parity",
        name="Predictive Parity",
        description="Positive-predictive-value difference between groups.",
        threshold=0.1,
        comparator="abs_lte",
        regulation_refs=("Fairness and Machine Learning",),
        implementation_status="full",
    ),
    "false_positive_rate_difference": MetricDefinition(
        key="false_positive_rate_difference",
        name="False Positive Rate Difference",
        description="Difference in false-positive rates between groups.",
        threshold=0.1,
        comparator="abs_lte",
        regulation_refs=("EU AI Act",),
        implementation_status="full",
    ),
    "false_negative_rate_difference": MetricDefinition(
        key="false_negative_rate_difference",
        name="False Negative Rate Difference",
        description="Difference in false-negative rates between groups.",
        threshold=0.1,
        comparator="abs_lte",
        regulation_refs=("EU AI Act",),
        implementation_status="full",
    ),
    "theil_index": MetricDefinition(
        key="theil_index",
        name="Theil Index",
        description="Gap in benefit inequality between groups.",
        threshold=0.1,
        comparator="abs_lte",
        regulation_refs=("AIF360 Theil Index",),
        implementation_status="full",
    ),
    "treatment_equality": MetricDefinition(
        key="treatment_equality",
        name="Treatment Equality",
        description="Ratio of FN/FP balance between groups.",
        threshold=1.25,
        comparator="between",
        regulation_refs=("AIF360 treatment equality",),
        implementation_status="full",
        lower_threshold=0.8,
    ),
    "statistical_parity_ratio": MetricDefinition(
        key="statistical_parity_ratio",
        name="Statistical Parity Ratio",
        description="Selection-rate ratio between groups.",
        threshold=0.8,
        comparator="gte",
        regulation_refs=("EEOC 4/5ths Rule",),
        implementation_status="full",
    ),
    "conditional_demographic_parity": MetricDefinition(
        key="conditional_demographic_parity",
        name="Conditional Demographic Parity",
        description="Weighted selection-rate gap after conditioning on legitimate factors.",
        threshold=0.1,
        comparator="abs_lte",
        regulation_refs=("Fairness and Machine Learning",),
        implementation_status="surrogate",
        notes="Uses available conditioning columns or derived experience/education buckets.",
    ),
    "counterfactual_fairness": MetricDefinition(
        key="counterfactual_fairness",
        name="Counterfactual Fairness",
        description="Prediction flip rate after protected-attribute substitution.",
        threshold=0.05,
        comparator="abs_lte",
        regulation_refs=("Kusner et al. 2017",),
        implementation_status="surrogate",
        notes="Local mode flips protected attributes without a structural causal model.",
    ),
    "shap_feature_attribution": MetricDefinition(
        key="shap_feature_attribution",
        name="SHAP Feature Attribution",
        description="Top proxy-feature disparity score by protected group.",
        threshold=0.3,
        comparator="abs_lte",
        regulation_refs=("SHAP",),
        implementation_status="surrogate",
        notes="Uses linear contribution gaps as a SHAP-style local surrogate.",
    ),
}


def list_metric_definitions() -> list[MetricDefinitionResponse]:
    return [
        MetricDefinitionResponse(
            key=definition.key,
            name=definition.name,
            description=definition.description,
            threshold=definition.threshold,
            comparator=definition.comparator,
            regulation_refs=list(definition.regulation_refs),
            implementation_status=definition.implementation_status,
            notes=definition.notes,
        )
        for definition in METRIC_CATALOG.values()
    ]


class FairnessMetricsEngine:
    def compute_group_metrics(
        self,
        *,
        evaluation_frame: pd.DataFrame,
        labels: np.ndarray,
        predictions: np.ndarray,
        stage: str,
        protected_attributes: list[str],
        conditional_attributes: list[str],
        counterfactuals: list[CounterfactualAudit],
        feature_attributions: list[FeatureAttribution],
    ) -> list[MetricResult]:
        results: list[MetricResult] = []
        label_array = labels.astype(int)
        prediction_array = predictions.astype(int)

        for protected_attribute in protected_attributes:
            values = evaluation_frame[protected_attribute].astype(str)
            counts = values.value_counts()
            if len(counts) < 2:
                continue
            reference_group = counts.index[0]
            comparison_groups = counts.index[1:]

            for comparison_group in comparison_groups:
                mask_a = values == comparison_group
                mask_b = values == reference_group

                selection_a = float(np.mean(prediction_array[mask_a.values] == 1))
                selection_b = float(np.mean(prediction_array[mask_b.values] == 1))
                tpr_a, fpr_a, fnr_a, ppv_a = _confusion_rates(
                    label_array[mask_a.values],
                    prediction_array[mask_a.values],
                )
                tpr_b, fpr_b, fnr_b, ppv_b = _confusion_rates(
                    label_array[mask_b.values],
                    prediction_array[mask_b.values],
                )

                metric_values = {
                    "disparate_impact": safe_divide(selection_a, selection_b),
                    "demographic_parity_difference": selection_a - selection_b,
                    "equal_opportunity_difference": tpr_a - tpr_b,
                    "average_odds_difference": 0.5 * ((fpr_a - fpr_b) + (tpr_a - tpr_b)),
                    "predictive_parity": ppv_a - ppv_b,
                    "false_positive_rate_difference": fpr_a - fpr_b,
                    "false_negative_rate_difference": fnr_a - fnr_b,
                    "theil_index": _group_theil_gap(
                        label_array[mask_a.values],
                        prediction_array[mask_a.values],
                        label_array[mask_b.values],
                        prediction_array[mask_b.values],
                    ),
                    "treatment_equality": safe_divide(
                        fnr_a,
                        max(fpr_a, 1e-6),
                        default=0.0,
                    )
                    / max(
                        safe_divide(fnr_b, max(fpr_b, 1e-6), default=1.0),
                        1e-6,
                    ),
                    "statistical_parity_ratio": safe_divide(selection_a, selection_b),
                    "conditional_demographic_parity": _conditional_demographic_parity(
                        evaluation_frame=evaluation_frame,
                        predictions=prediction_array,
                        protected_attribute=protected_attribute,
                        comparison_group=comparison_group,
                        reference_group=reference_group,
                        conditional_attributes=conditional_attributes,
                    ),
                }

                for metric_key, value in metric_values.items():
                    definition = METRIC_CATALOG[metric_key]
                    results.append(
                        _build_metric_result(
                            definition=definition,
                            stage=stage,
                            protected_attribute=protected_attribute,
                            group_a=str(comparison_group),
                            group_b=str(reference_group),
                            value=float(value),
                        )
                    )

            for counterfactual in counterfactuals:
                if counterfactual.protected_attribute != protected_attribute:
                    continue
                if counterfactual.stage != stage:
                    continue
                definition = METRIC_CATALOG["counterfactual_fairness"]
                results.append(
                    _build_metric_result(
                        definition=definition,
                        stage=stage,
                        protected_attribute=protected_attribute,
                        group_a="counterfactual_flip_rate",
                        group_b="stable_prediction",
                        value=float(counterfactual.flip_rate),
                    )
                )

            attribution_scores = [
                (
                    attribution.baseline_contribution_gap
                    if stage == "baseline"
                    else attribution.verification_contribution_gap
                )
                for attribution in feature_attributions
                if attribution.protected_attribute == protected_attribute
            ]
            if attribution_scores:
                definition = METRIC_CATALOG["shap_feature_attribution"]
                results.append(
                    _build_metric_result(
                        definition=definition,
                        stage=stage,
                        protected_attribute=protected_attribute,
                        group_a="top_proxy_feature",
                        group_b="reference",
                        value=float(max(abs(score) for score in attribution_scores)),
                    )
                )

        return results


def _confusion_rates(labels: np.ndarray, predictions: np.ndarray) -> tuple[float, float, float, float]:
    true_positive = int(np.sum((labels == 1) & (predictions == 1)))
    false_positive = int(np.sum((labels == 0) & (predictions == 1)))
    true_negative = int(np.sum((labels == 0) & (predictions == 0)))
    false_negative = int(np.sum((labels == 1) & (predictions == 0)))
    tpr = safe_divide(true_positive, true_positive + false_negative)
    fpr = safe_divide(false_positive, false_positive + true_negative)
    fnr = safe_divide(false_negative, false_negative + true_positive)
    ppv = safe_divide(true_positive, true_positive + false_positive)
    return tpr, fpr, fnr, ppv


def _theil_index(labels: np.ndarray, predictions: np.ndarray) -> float:
    benefit = 1.0 + predictions.astype(float) - labels.astype(float)
    mean_benefit = float(np.mean(benefit))
    if mean_benefit == 0.0:
        return 0.0
    ratios = np.clip(benefit / mean_benefit, 1e-6, None)
    return float(np.mean(ratios * np.log(ratios)))


def _group_theil_gap(
    labels_a: np.ndarray,
    predictions_a: np.ndarray,
    labels_b: np.ndarray,
    predictions_b: np.ndarray,
) -> float:
    return _theil_index(labels_a, predictions_a) - _theil_index(labels_b, predictions_b)


def _conditional_demographic_parity(
    *,
    evaluation_frame: pd.DataFrame,
    predictions: np.ndarray,
    protected_attribute: str,
    comparison_group: str,
    reference_group: str,
    conditional_attributes: list[str],
) -> float:
    candidate_columns = [
        column
        for column in conditional_attributes
        if column in evaluation_frame.columns
    ]
    if not candidate_columns:
        candidate_columns = [
            column
            for column in (
                "years_experience_bucket",
                "education_level_bucket",
                "resume_length_bucket",
            )
            if column in evaluation_frame.columns
        ]
    if not candidate_columns:
        return 0.0

    conditioning_column = candidate_columns[0]
    working = evaluation_frame[[protected_attribute, conditioning_column]].copy()
    working["__prediction"] = predictions

    weighted_gap = 0.0
    total_weight = 0.0

    for _, group_frame in working.groupby(conditioning_column):
        mask_a = group_frame[protected_attribute].astype(str) == comparison_group
        mask_b = group_frame[protected_attribute].astype(str) == reference_group
        if not mask_a.any() or not mask_b.any():
            continue
        selection_a = float(np.mean(group_frame.loc[mask_a, "__prediction"] == 1))
        selection_b = float(np.mean(group_frame.loc[mask_b, "__prediction"] == 1))
        weight = float(len(group_frame) / len(working))
        weighted_gap += weight * (selection_a - selection_b)
        total_weight += weight

    return safe_divide(weighted_gap, total_weight, default=0.0)


def _build_metric_result(
    *,
    definition: MetricDefinition,
    stage: str,
    protected_attribute: str,
    group_a: str,
    group_b: str,
    value: float,
) -> MetricResult:
    passed = _passes(definition, value)
    severity = _severity(definition, value, passed)
    return MetricResult(
        metric_key=definition.key,
        metric_name=definition.name,
        stage=stage,
        protected_attribute=protected_attribute,
        group_a=group_a,
        group_b=group_b,
        value=round(float(value), 4),
        threshold=definition.threshold,
        passed=passed,
        severity=severity,
        human_summary=_human_summary(definition, protected_attribute, group_a, group_b, value, passed),
        regulation_refs=list(definition.regulation_refs),
        notes=definition.notes,
    )


def _passes(definition: MetricDefinition, value: float) -> bool:
    if definition.comparator == "gte":
        return value >= definition.threshold
    if definition.comparator == "abs_lte":
        return abs(value) <= definition.threshold
    if definition.comparator == "between":
        lower = definition.lower_threshold if definition.lower_threshold is not None else 0.0
        return lower <= value <= definition.threshold
    return False


def _severity(
    definition: MetricDefinition,
    value: float,
    passed: bool,
) -> Severity:
    if passed:
        return Severity.LOW

    if definition.comparator == "gte":
        gap = definition.threshold - value
        if gap > definition.threshold * 0.4:
            return Severity.CRITICAL
        if gap > definition.threshold * 0.2:
            return Severity.HIGH
        return Severity.MEDIUM

    if definition.comparator == "abs_lte":
        ratio = abs(value) / max(definition.threshold, 1e-6)
        if ratio > 2.0:
            return Severity.CRITICAL
        if ratio > 1.5:
            return Severity.HIGH
        return Severity.MEDIUM

    lower = definition.lower_threshold if definition.lower_threshold is not None else 0.0
    if value < lower * 0.75 or value > definition.threshold * 1.25:
        return Severity.CRITICAL
    if value < lower or value > definition.threshold:
        return Severity.HIGH
    return Severity.MEDIUM


def _human_summary(
    definition: MetricDefinition,
    protected_attribute: str,
    group_a: str,
    group_b: str,
    value: float,
    passed: bool,
) -> str:
    outcome = "passes" if passed else "fails"
    return (
        f"{definition.name} for '{protected_attribute}' comparing '{group_a}' against "
        f"'{group_b}' is {value:.4f}, which {outcome} the configured threshold."
    )


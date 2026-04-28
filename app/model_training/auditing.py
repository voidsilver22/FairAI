from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)


def _selection_rate(frame: pd.DataFrame) -> float:
    if frame.empty:
        return 0.0
    return float(frame["Predicted_Label"].mean())


def _true_positive_rate(frame: pd.DataFrame) -> float:
    positives = frame[frame["True_Label"] == 1]
    if positives.empty:
        return 0.0
    return float((positives["Predicted_Label"] == 1).mean())


def _false_negative_rate(frame: pd.DataFrame) -> float:
    positives = frame[frame["True_Label"] == 1]
    if positives.empty:
        return 0.0
    return float((positives["Predicted_Label"] == 0).mean())


def _false_positive_rate(frame: pd.DataFrame) -> float:
    negatives = frame[frame["True_Label"] == 0]
    if negatives.empty:
        return 0.0
    return float((negatives["Predicted_Label"] == 1).mean())


def _mean_group_rate(
    frame: pd.DataFrame,
    *,
    attribute_name: str,
    groups: list[str],
    rate_fn,
) -> float:
    rates: list[float] = []
    for group in groups:
        slice_frame = frame[frame[attribute_name] == group]
        if slice_frame.empty:
            continue
        rates.append(rate_fn(slice_frame))
    if not rates:
        return 0.0
    return float(sum(rates) / len(rates))


@dataclass(frozen=True, slots=True)
class AuditSliceConfig:
    attribute_name: str
    privileged_label: str
    unprivileged_label: str
    privileged_values: list[str]


DEFAULT_AUDIT_SLICES: tuple[AuditSliceConfig, ...] = (
    AuditSliceConfig(
        attribute_name="gender",
        privileged_label="Male",
        unprivileged_label="Female",
        privileged_values=["Male"],
    ),
    AuditSliceConfig(
        attribute_name="age_group",
        privileged_label="35-44",
        unprivileged_label="21-26",
        privileged_values=["35-44"],
    ),
    AuditSliceConfig(
        attribute_name="college_tier",
        privileged_label="Tier 1/Tier 2",
        unprivileged_label="Tier 3",
        privileged_values=["Tier 1", "Tier 2"],
    ),
    AuditSliceConfig(
        attribute_name="region",
        privileged_label="Non-Metro",
        unprivileged_label="Metro",
        privileged_values=["Non-Metro"],
    ),
)


class FairnessAuditor:
    def __init__(self, dataframe: pd.DataFrame, score_col: str, threshold: float) -> None:
        if score_col not in dataframe.columns:
            raise ValueError(f"Score column '{score_col}' was not found in the scored dataset.")
        if "matched_score" not in dataframe.columns:
            raise ValueError("The scored dataset must include a 'matched_score' column.")

        self.df = dataframe.copy()
        self.threshold = threshold
        self.df["Predicted_Label"] = (self.df[score_col] >= threshold).astype(int)
        self.df["True_Label"] = (self.df["matched_score"] >= threshold).astype(int)

    def evaluate_slice(self, config: AuditSliceConfig) -> dict:
        if config.attribute_name not in self.df.columns:
            raise ValueError(
                f"Protected attribute '{config.attribute_name}' was not found in the scored dataset."
            )

        comparison_groups = [*config.privileged_values, config.unprivileged_label]
        frame = self.df[self.df[config.attribute_name].isin(comparison_groups)].copy()
        if frame.empty:
            raise ValueError(
                f"No rows were found for audit slice '{config.attribute_name}' using "
                f"groups {comparison_groups}."
            )

        privileged_frame = frame[frame[config.attribute_name].isin(config.privileged_values)]
        unprivileged_frame = frame[frame[config.attribute_name] == config.unprivileged_label]
        if privileged_frame.empty or unprivileged_frame.empty:
            raise ValueError(
                f"Audit slice '{config.attribute_name}' requires both privileged and "
                f"unprivileged groups to be present."
            )

        sr_unpriv = _selection_rate(unprivileged_frame)
        tpr_unpriv = _true_positive_rate(unprivileged_frame)
        fnr_unpriv = _false_negative_rate(unprivileged_frame)
        fpr_unpriv = _false_positive_rate(unprivileged_frame)

        sr_priv = _mean_group_rate(
            frame,
            attribute_name=config.attribute_name,
            groups=config.privileged_values,
            rate_fn=_selection_rate,
        )
        tpr_priv = _mean_group_rate(
            frame,
            attribute_name=config.attribute_name,
            groups=config.privileged_values,
            rate_fn=_true_positive_rate,
        )
        fnr_priv = _mean_group_rate(
            frame,
            attribute_name=config.attribute_name,
            groups=config.privileged_values,
            rate_fn=_false_negative_rate,
        )
        fpr_priv = _mean_group_rate(
            frame,
            attribute_name=config.attribute_name,
            groups=config.privileged_values,
            rate_fn=_false_positive_rate,
        )

        disparate_impact = _safe_ratio(sr_unpriv, sr_priv)
        equal_opportunity_difference = tpr_unpriv - tpr_priv
        false_negative_rate_difference = fnr_unpriv - fnr_priv
        false_positive_rate_difference = fpr_unpriv - fpr_priv

        metrics = [
            self._format_metric(
                name="Disparate Impact",
                value=disparate_impact,
                threshold=0.80,
                passed=disparate_impact >= 0.80,
                description=(
                    "Unprivileged group is selected at "
                    f"{disparate_impact * 100:.1f}% the rate of the privileged group."
                ),
            ),
            self._format_metric(
                name="Equal Opportunity Difference",
                value=equal_opportunity_difference,
                threshold=-0.10,
                passed=equal_opportunity_difference >= -0.10,
                description=(
                    f"Qualified {config.unprivileged_label} candidates have a "
                    f"{equal_opportunity_difference * 100:.1f}% difference in selection rate "
                    f"vs {config.privileged_label}."
                ),
            ),
            self._format_metric(
                name="False Negative Rate Difference",
                value=false_negative_rate_difference,
                threshold=0.10,
                passed=false_negative_rate_difference <= 0.10,
                description=(
                    f"{config.unprivileged_label} candidates are incorrectly rejected "
                    f"{false_negative_rate_difference * 100:.1f}% more often."
                ),
            ),
            self._format_metric(
                name="False Positive Rate Difference",
                value=false_positive_rate_difference,
                threshold=0.10,
                passed=false_positive_rate_difference <= 0.10,
                description=(
                    f"{config.unprivileged_label} candidates are incorrectly accepted "
                    f"{false_positive_rate_difference * 100:.1f}% more often."
                ),
            ),
        ]

        failed_count = sum(1 for metric in metrics if not metric["passed"])
        audit_status = "FAIL" if (disparate_impact < 0.80 or failed_count >= 3) else "PASS"

        return {
            "audit_status": audit_status,
            "evaluated_group": {
                "attribute": config.attribute_name,
                "privileged": config.privileged_label,
                "unprivileged": config.unprivileged_label,
            },
            "metrics": metrics,
        }

    def run_full_audit(self) -> dict[str, dict]:
        return {
            config.attribute_name: self.evaluate_slice(config)
            for config in DEFAULT_AUDIT_SLICES
        }

    @staticmethod
    def _format_metric(
        *,
        name: str,
        value: float,
        threshold: float,
        passed: bool,
        description: str,
    ) -> dict:
        return {
            "name": name,
            "value": round(float(value), 3),
            "threshold": threshold,
            "passed": bool(passed),
            "description": description,
        }


def generate_workspace_audit_report(
    *,
    baseline_csv_path: Path,
    fairlens_csv_path: Path,
    baseline_score_col: str = "Model_Predicted_Score",
    fairlens_score_col: str = "FairLens_Predicted_Score",
    baseline_threshold: float = 0.70,
    fairlens_threshold: float = 0.685,
    output_json_path: Path | None = None,
) -> dict[str, dict[str, dict]]:
    baseline_frame = pd.read_csv(baseline_csv_path)
    fairlens_frame = pd.read_csv(fairlens_csv_path)

    payload = {
        "Baseline": FairnessAuditor(
            baseline_frame,
            score_col=baseline_score_col,
            threshold=baseline_threshold,
        ).run_full_audit(),
        "FairLens": FairnessAuditor(
            fairlens_frame,
            score_col=fairlens_score_col,
            threshold=fairlens_threshold,
        ).run_full_audit(),
    }

    if output_json_path is not None:
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return payload

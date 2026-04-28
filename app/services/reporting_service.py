from __future__ import annotations

from app.models.domain import FairnessReport


class ReportingService:
    def build_markdown_report(self, report: FairnessReport) -> str:
        failing_baseline = [metric for metric in report.baseline_metrics if not metric.passed]
        failing_verification = [metric for metric in report.verification_metrics if not metric.passed]

        lines = [
            f"# FairLens Audit Report: {report.job_id}",
            "",
            "## Overview",
            f"- Rows audited: {report.dataset_profile.row_count}",
            f"- Resume text column: {report.dataset_profile.resume_text_column}",
            f"- Baseline accuracy: {report.baseline_performance.accuracy}",
            f"- Verification accuracy: {report.verification_performance.accuracy}",
            f"- Fairness improvement: {report.summary['fairness_improvement']}",
            f"- Accuracy delta: {report.summary['accuracy_delta']}",
            "",
            "## Baseline Findings",
        ]

        if failing_baseline:
            lines.extend(f"- {metric.human_summary}" for metric in failing_baseline[:10])
        else:
            lines.append("- No baseline metric failures were detected.")

        lines.extend(["", "## Verification Findings"])
        if failing_verification:
            lines.extend(f"- {metric.human_summary}" for metric in failing_verification[:10])
        else:
            lines.append("- All verification metrics passed for the evaluated comparisons.")

        lines.extend(["", "## Remediation"])
        lines.append(f"- Strategy: {report.remediation.strategy}")
        lines.append(f"- Notes: {report.remediation.notes}")

        if report.feature_attributions:
            lines.extend(["", "## Proxy Features"])
            for attribution in report.feature_attributions[:10]:
                lines.append(
                    f"- {attribution.protected_attribute}: {attribution.feature_name} "
                    f"(before={attribution.baseline_contribution_gap}, "
                    f"after={attribution.verification_contribution_gap})"
                )

        return "\n".join(lines)


from __future__ import annotations

import pandas as pd

from app.ml.pipeline import FairLensPipeline, PipelineRequest
from app.models.domain import AuditInputSpec


def test_pipeline_generates_report_from_file_uri_request(sample_records):
    frame = pd.DataFrame.from_records(sample_records)
    pipeline = FairLensPipeline(counterfactual_sample_size=24)
    report = pipeline.execute(
        request=PipelineRequest(
            job_id="pipeline-test",
            file_uri="memory://resumes.csv",
            config=AuditInputSpec(
                source_uri="memory://resumes.csv",
                resume_text_column="resume_text",
                label_column="hired",
                positive_label=1,
                protected_attributes=["gender"],
                conditional_attributes=["years_experience_bucket"],
                fairness_weight=0.35,
            ),
        ),
        data_loader=lambda _file_uri: frame,
    ).report

    baseline_keys = {metric.metric_key for metric in report.baseline_metrics}
    verification_keys = {metric.metric_key for metric in report.verification_metrics}

    assert report.dataset_profile.row_count == len(sample_records)
    assert "disparate_impact" in baseline_keys
    assert "counterfactual_fairness" in verification_keys
    assert report.remediation.strategy == "adversarial_debias_surrogate"
    assert len(report.counterfactuals) == 2
    assert report.summary["verification_metric_pass_rate"] >= 0.0

from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.metrics import FairnessMetricsEngine
from app.models.domain import CounterfactualAudit
from app.models.enums import Severity


def test_metrics_engine_computes_expected_disparate_impact():
    frame = pd.DataFrame(
        {
            "gender": ["male"] * 10 + ["female"] * 10,
            "years_experience_bucket": ["3-5"] * 20,
        }
    )
    labels = np.array([1] * 8 + [0] * 2 + [1] * 8 + [0] * 2)
    predictions = np.array([1] * 8 + [0] * 2 + [1] * 4 + [0] * 6)

    metrics = FairnessMetricsEngine().compute_group_metrics(
        evaluation_frame=frame,
        labels=labels,
        predictions=predictions,
        stage="baseline",
        protected_attributes=["gender"],
        conditional_attributes=["years_experience_bucket"],
        counterfactuals=[
            CounterfactualAudit(
                protected_attribute="gender",
                stage="baseline",
                flip_rate=0.08,
                sample_size=20,
                severity=Severity.CRITICAL,
            )
        ],
        feature_attributions=[],
    )

    disparate_impact = next(
        metric for metric in metrics if metric.metric_key == "disparate_impact"
    )
    counterfactual = next(
        metric for metric in metrics if metric.metric_key == "counterfactual_fairness"
    )

    assert round(disparate_impact.value, 2) == 0.5
    assert disparate_impact.passed is False
    assert counterfactual.value == 0.08
    assert counterfactual.passed is False


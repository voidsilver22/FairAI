from __future__ import annotations

from typing import Callable

import pandas as pd

from app.models.domain import CounterfactualAudit, CounterfactualFlip
from app.models.enums import Severity


def run_counterfactual_audit(
    frame: pd.DataFrame,
    *,
    protected_attribute: str,
    score_callable: Callable[[pd.DataFrame], list[int]],
    stage: str,
    n_samples: int,
) -> CounterfactualAudit:
    sampled = frame.sample(min(len(frame), n_samples), random_state=42)
    possible_values = sampled[protected_attribute].astype(str).unique().tolist()
    flip_examples: list[CounterfactualFlip] = []
    flip_count = 0
    comparisons = 0

    for row_index, row in sampled.iterrows():
        original_value = str(row[protected_attribute])
        original_prediction = int(score_callable(pd.DataFrame([row]))[0])

        for alternative_value in possible_values:
            if alternative_value == original_value:
                continue
            twin = row.copy()
            twin[protected_attribute] = alternative_value
            alternative_prediction = int(score_callable(pd.DataFrame([twin]))[0])
            comparisons += 1
            if alternative_prediction != original_prediction:
                flip_count += 1
                if len(flip_examples) < 8:
                    flip_examples.append(
                        CounterfactualFlip(
                            row_index=int(row_index),
                            original_group=original_value,
                            alternative_group=alternative_value,
                            original_prediction=original_prediction,
                            alternative_prediction=alternative_prediction,
                        )
                    )

    flip_rate = round(float(flip_count / max(comparisons, 1)), 4)
    severity = (
        Severity.CRITICAL
        if flip_rate > 0.05
        else Severity.HIGH
        if flip_rate > 0.02
        else Severity.LOW
    )
    return CounterfactualAudit(
        protected_attribute=protected_attribute,
        stage=stage,
        flip_rate=flip_rate,
        sample_size=int(len(sampled)),
        severity=severity,
        examples=flip_examples,
    )


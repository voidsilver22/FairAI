from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.baseline import LinearModelState
from app.models.domain import FeatureAttribution


class ExplainabilityService:
    """Linear contribution-based proxy attribution used as a SHAP-style surrogate."""

    def build_feature_attributions(
        self,
        *,
        baseline_model: LinearModelState,
        verification_model: LinearModelState,
        baseline_feature_frame: pd.DataFrame,
        verification_feature_frame: pd.DataFrame,
        protected_frame: pd.DataFrame,
        top_k: int = 5,
    ) -> list[FeatureAttribution]:
        common_features = [
            feature_name
            for feature_name in baseline_model.feature_names
            if feature_name in verification_model.feature_names
        ]
        if not common_features:
            return []

        baseline_std_full = baseline_model.standardize_frame(baseline_feature_frame)
        verification_std_full = verification_model.standardize_frame(verification_feature_frame)
        baseline_indices = [
            baseline_model.feature_names.index(feature_name) for feature_name in common_features
        ]
        verification_indices = [
            verification_model.feature_names.index(feature_name)
            for feature_name in common_features
        ]
        baseline_std = baseline_std_full[:, baseline_indices]
        verification_std = verification_std_full[:, verification_indices]
        baseline_weights = baseline_model.weights[baseline_indices]
        verification_weights = verification_model.weights[verification_indices]
        baseline_contributions = baseline_std * baseline_weights
        verification_contributions = verification_std * verification_weights

        attributions: list[FeatureAttribution] = []

        for protected_attribute in protected_frame.columns:
            values = protected_frame[protected_attribute].astype(str)
            counts = values.value_counts()
            if len(counts) < 2:
                continue
            reference_group = counts.index[0]

            for group in counts.index[1:]:
                mask_a = values == group
                mask_b = values == reference_group
                if not mask_a.any() or not mask_b.any():
                    continue

                baseline_gap = (
                    baseline_contributions[mask_a.values].mean(axis=0)
                    - baseline_contributions[mask_b.values].mean(axis=0)
                )
                verification_gap = (
                    verification_contributions[mask_a.values].mean(axis=0)
                    - verification_contributions[mask_b.values].mean(axis=0)
                )
                ranked_indices = np.argsort(np.abs(baseline_gap))[::-1][:top_k]

                for index in ranked_indices:
                    attributions.append(
                        FeatureAttribution(
                            protected_attribute=protected_attribute,
                            feature_name=common_features[index],
                            disparity_score=round(float(abs(baseline_gap[index])), 4),
                            baseline_contribution_gap=round(float(baseline_gap[index]), 4),
                            verification_contribution_gap=round(
                                float(verification_gap[index]),
                                4,
                            ),
                            explanation=(
                                f"Feature '{common_features[index]}' showed the largest "
                                f"contribution gap for group '{group}' vs '{reference_group}'."
                            ),
                        )
                    )

        return attributions

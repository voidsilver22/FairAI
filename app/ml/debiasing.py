from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.ml.baseline import LinearModelState, LinearModelTrainer, PredictionBundle
from app.ml.utils import cross_entropy_loss, normalize_signal, sigmoid
from app.models.domain import DebiasingIteration, RemediationSummary


@dataclass(slots=True)
class DebiasingResult:
    model: LinearModelState
    prediction_bundle: PredictionBundle
    remediation: RemediationSummary


class AdversarialDebiaser:
    """
    Deterministic surrogate for a GRL-based adversarial debiaser.

    The implementation explicitly trains simple adversary classifiers against protected
    attribute indicators and shrinks predictor weights that carry the strongest
    demographic signal. This is intentionally lightweight and testable, while keeping
    the architecture swappable for a real PyTorch GRL implementation later.
    """

    def __init__(
        self,
        trainer: LinearModelTrainer,
        *,
        iterations: int = 5,
    ) -> None:
        self.trainer = trainer
        self.iterations = iterations

    def fit(
        self,
        feature_frame: pd.DataFrame,
        labels: np.ndarray,
        protected_frame: pd.DataFrame,
        train_mask: np.ndarray,
        test_mask: np.ndarray,
        *,
        fairness_weight: float,
    ) -> DebiasingResult:
        train_features = feature_frame.loc[train_mask]
        test_features = feature_frame.loc[test_mask]
        train_labels = labels[train_mask]
        test_labels = labels[test_mask]

        predictor = self.trainer.fit_dataframe(
            train_features,
            train_labels,
            model_name="debiased_predictor",
        )
        standardized_train = predictor.standardize_frame(train_features)

        protected_indicators = pd.get_dummies(
            protected_frame.astype(str),
            prefix=protected_frame.columns,
            dtype=float,
        )
        protected_train = protected_indicators.loc[train_mask]

        weights = predictor.weights.copy()
        intercept = predictor.intercept
        history: list[DebiasingIteration] = []

        for iteration in range(1, self.iterations + 1):
            adversary_coefficients: list[np.ndarray] = []

            for column in protected_train.columns:
                target = protected_train[column].to_numpy(dtype=float)
                if len(np.unique(target)) < 2:
                    continue
                adversary = self.trainer.fit_standardized(
                    standardized_train,
                    target,
                    feature_names=predictor.feature_names,
                    model_name=f"adversary_{column}",
                )
                adversary_coefficients.append(np.abs(adversary.weights))

            aggregate_signal = (
                np.mean(adversary_coefficients, axis=0)
                if adversary_coefficients
                else np.zeros_like(weights)
            )
            normalized_signal = normalize_signal(aggregate_signal)
            weights = weights * (1.0 - fairness_weight * normalized_signal)
            intercept = self.trainer.calibrate_intercept(
                standardized_train,
                train_labels,
                weights,
                intercept,
            )
            probabilities = sigmoid(standardized_train @ weights + intercept)
            history.append(
                DebiasingIteration(
                    iteration=iteration,
                    predictor_loss=round(
                        cross_entropy_loss(train_labels.astype(float), probabilities),
                        4,
                    ),
                    adversary_signal=round(float(np.mean(np.abs(aggregate_signal))), 4),
                    fairness_penalty=round(float(np.mean(normalized_signal)), 4),
                )
            )

        final_model = LinearModelState(
            model_name="debiased_predictor",
            feature_names=predictor.feature_names,
            means=predictor.means,
            stds=predictor.stds,
            intercept=intercept,
            weights=weights,
        )

        prediction_bundle = self.trainer.evaluate(final_model, test_features, test_labels)
        remediation = RemediationSummary(
            strategy="adversarial_debias_surrogate",
            fairness_weight=round(float(fairness_weight), 4),
            iterations=history,
            notes=(
                "Local mode uses a deterministic adversary-guided coefficient shrinkage "
                "loop. Replace with a PyTorch gradient reversal network for full-scale deployment."
            ),
        )
        return DebiasingResult(
            model=final_model,
            prediction_bundle=prediction_bundle,
            remediation=remediation,
        )


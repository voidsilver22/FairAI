from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.ml.utils import (
    BinaryPerformance,
    compute_binary_performance,
    cross_entropy_loss,
    sigmoid,
)
from app.models.domain import LinearModelArtifact, ModelPerformance


@dataclass(slots=True)
class LinearModelState:
    model_name: str
    feature_names: list[str]
    means: np.ndarray
    stds: np.ndarray
    intercept: float
    weights: np.ndarray

    def align_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        aligned = frame.copy()
        for feature_name in self.feature_names:
            if feature_name not in aligned.columns:
                aligned[feature_name] = 0.0
        return aligned[self.feature_names].astype(float)

    def standardize_frame(self, frame: pd.DataFrame) -> np.ndarray:
        matrix = self.align_frame(frame).to_numpy(dtype=float)
        return self.standardize_matrix(matrix)

    def standardize_matrix(self, matrix: np.ndarray) -> np.ndarray:
        return (matrix - self.means) / self.stds

    def predict_probabilities(self, frame: pd.DataFrame) -> np.ndarray:
        standardized = self.standardize_frame(frame)
        return sigmoid(standardized @ self.weights + self.intercept)

    def predict_binary(self, frame: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        return (self.predict_probabilities(frame) >= threshold).astype(int)

    def to_artifact(self) -> LinearModelArtifact:
        return LinearModelArtifact(
            model_name=self.model_name,
            intercept=round(float(self.intercept), 6),
            coefficients={
                name: round(float(weight), 6)
                for name, weight in zip(self.feature_names, self.weights, strict=False)
            },
            feature_means={
                name: round(float(value), 6)
                for name, value in zip(self.feature_names, self.means, strict=False)
            },
            feature_stds={
                name: round(float(value), 6)
                for name, value in zip(self.feature_names, self.stds, strict=False)
            },
        )

    @classmethod
    def from_artifact(cls, artifact: LinearModelArtifact) -> "LinearModelState":
        feature_names = list(artifact.coefficients.keys())
        return cls(
            model_name=artifact.model_name,
            feature_names=feature_names,
            means=np.array([artifact.feature_means[name] for name in feature_names], dtype=float),
            stds=np.array([artifact.feature_stds[name] for name in feature_names], dtype=float),
            intercept=float(artifact.intercept),
            weights=np.array([artifact.coefficients[name] for name in feature_names], dtype=float),
        )


@dataclass(slots=True)
class PredictionBundle:
    probabilities: np.ndarray
    predictions: np.ndarray
    performance: ModelPerformance


class LinearModelTrainer:
    """Simple deterministic logistic regression trainer using NumPy."""

    def __init__(
        self,
        *,
        learning_rate: float = 0.1,
        epochs: int = 300,
        l2_penalty: float = 0.001,
    ) -> None:
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.l2_penalty = l2_penalty

    def fit_dataframe(
        self,
        frame: pd.DataFrame,
        labels: np.ndarray,
        *,
        model_name: str,
        initial_weights: np.ndarray | None = None,
        initial_intercept: float = 0.0,
    ) -> LinearModelState:
        matrix = frame.to_numpy(dtype=float)
        means = matrix.mean(axis=0)
        stds = matrix.std(axis=0)
        stds = np.where(stds == 0.0, 1.0, stds)
        standardized = (matrix - means) / stds
        weights, intercept = self._optimize(
            standardized,
            labels.astype(float),
            initial_weights=initial_weights,
            initial_intercept=initial_intercept,
        )
        return LinearModelState(
            model_name=model_name,
            feature_names=list(frame.columns),
            means=means,
            stds=stds,
            intercept=intercept,
            weights=weights,
        )

    def fit_standardized(
        self,
        matrix: np.ndarray,
        labels: np.ndarray,
        *,
        feature_names: list[str],
        model_name: str,
        initial_weights: np.ndarray | None = None,
        initial_intercept: float = 0.0,
    ) -> LinearModelState:
        weights, intercept = self._optimize(
            matrix,
            labels.astype(float),
            initial_weights=initial_weights,
            initial_intercept=initial_intercept,
        )
        return LinearModelState(
            model_name=model_name,
            feature_names=feature_names,
            means=np.zeros(matrix.shape[1]),
            stds=np.ones(matrix.shape[1]),
            intercept=intercept,
            weights=weights,
        )

    def calibrate_intercept(
        self,
        standardized_matrix: np.ndarray,
        labels: np.ndarray,
        weights: np.ndarray,
        intercept: float,
        *,
        steps: int = 50,
    ) -> float:
        updated = intercept
        label_array = labels.astype(float)
        for _ in range(steps):
            probabilities = sigmoid(standardized_matrix @ weights + updated)
            gradient = float(np.mean(probabilities - label_array))
            updated -= self.learning_rate * gradient
        return float(updated)

    def evaluate(
        self,
        model: LinearModelState,
        frame: pd.DataFrame,
        labels: np.ndarray,
    ) -> PredictionBundle:
        probabilities = model.predict_probabilities(frame)
        predictions = (probabilities >= 0.5).astype(int)
        performance = self._performance_from_arrays(labels, predictions)
        return PredictionBundle(
            probabilities=probabilities,
            predictions=predictions,
            performance=performance,
        )

    def _optimize(
        self,
        matrix: np.ndarray,
        labels: np.ndarray,
        *,
        initial_weights: np.ndarray | None = None,
        initial_intercept: float = 0.0,
    ) -> tuple[np.ndarray, float]:
        weights = (
            initial_weights.astype(float).copy()
            if initial_weights is not None
            else np.zeros(matrix.shape[1], dtype=float)
        )
        intercept = float(initial_intercept)

        for _ in range(self.epochs):
            logits = matrix @ weights + intercept
            probabilities = sigmoid(logits)
            errors = probabilities - labels
            gradient_weights = (matrix.T @ errors) / len(matrix)
            gradient_weights += self.l2_penalty * weights
            gradient_intercept = float(np.mean(errors))
            weights -= self.learning_rate * gradient_weights
            intercept -= self.learning_rate * gradient_intercept

        return weights, intercept

    def loss(self, model: LinearModelState, frame: pd.DataFrame, labels: np.ndarray) -> float:
        probabilities = model.predict_probabilities(frame)
        return cross_entropy_loss(labels.astype(float), probabilities)

    def _performance_from_arrays(
        self,
        labels: np.ndarray,
        predictions: np.ndarray,
    ) -> ModelPerformance:
        performance: BinaryPerformance = compute_binary_performance(labels, predictions)
        return ModelPerformance(
            accuracy=performance.accuracy,
            precision=performance.precision,
            recall=performance.recall,
            positive_rate=performance.positive_rate,
        )

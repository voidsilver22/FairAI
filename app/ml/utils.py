from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -50.0, 50.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def safe_divide(
    numerator: float | int,
    denominator: float | int,
    *,
    default: float = 0.0,
) -> float:
    if denominator == 0:
        return default
    return float(numerator) / float(denominator)


def deterministic_test_mask(
    size: int,
    *,
    modulus: int = 5,
) -> np.ndarray:
    indices = np.arange(size)
    return indices % modulus == 0


def normalize_signal(values: np.ndarray) -> np.ndarray:
    max_value = float(np.max(np.abs(values))) if values.size else 0.0
    if max_value == 0.0:
        return np.zeros_like(values)
    return values / max_value


def cross_entropy_loss(labels: np.ndarray, probabilities: np.ndarray) -> float:
    clipped = np.clip(probabilities, 1e-6, 1.0 - 1e-6)
    return float(
        -np.mean(labels * np.log(clipped) + (1.0 - labels) * np.log(1.0 - clipped))
    )


@dataclass(slots=True)
class BinaryPerformance:
    accuracy: float
    precision: float
    recall: float
    positive_rate: float


def compute_binary_performance(
    labels: np.ndarray,
    predictions: np.ndarray,
) -> BinaryPerformance:
    true_positive = int(np.sum((labels == 1) & (predictions == 1)))
    false_positive = int(np.sum((labels == 0) & (predictions == 1)))
    false_negative = int(np.sum((labels == 1) & (predictions == 0)))
    accuracy = float(np.mean(labels == predictions))
    precision = safe_divide(true_positive, true_positive + false_positive)
    recall = safe_divide(true_positive, true_positive + false_negative)
    positive_rate = float(np.mean(predictions == 1))
    return BinaryPerformance(
        accuracy=round(accuracy, 4),
        precision=round(precision, 4),
        recall=round(recall, 4),
        positive_rate=round(positive_rate, 4),
    )


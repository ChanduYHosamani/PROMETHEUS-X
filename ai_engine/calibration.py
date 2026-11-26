"""Confidence calibration, severity estimation, and distribution-shift metrics."""

from dataclasses import dataclass
from typing import Dict, List

import numpy as np


@dataclass(frozen=True)
class SeverityThresholds:
    low_max: float = 0.35
    medium_max: float = 0.65
    high_max: float = 0.85


def classify_severity(
    normalized_score: float,
    thresholds: SeverityThresholds = SeverityThresholds(),
) -> str:
    """Map a calibrated [0, 1] anomaly score to a severity tier."""
    if normalized_score < thresholds.low_max:
        return "low"
    if normalized_score < thresholds.medium_max:
        return "medium"
    if normalized_score < thresholds.high_max:
        return "high"
    return "critical"


def calibrate_image_scores(scores: List[float]) -> Dict[str, float]:
    """Calculate image-level threshold statistics from normal calibration images."""
    values = np.asarray(scores, dtype=np.float64)

    if values.size == 0:
        raise ValueError("At least one calibration image score is required.")

    if not np.all(np.isfinite(values)):
        raise ValueError("Calibration scores must all be finite.")

    mean = float(np.mean(values))
    std = float(np.std(values))
    maximum = float(np.max(values))

    margin = max(std * 0.1, abs(maximum) * 0.01, 1e-6)
    threshold = maximum + margin
    scale = max(std, abs(threshold) * 0.05, 1e-4)

    return {
        "image_score_mean": mean,
        "image_score_std": std,
        "image_score_max": maximum,
        "image_score_threshold": float(threshold),
        "image_score_scale": float(scale),
        "calibration_image_count": int(values.size),
    }


def normalize_calibrated_score(raw_score: float, stats: Dict[str, float]) -> float:
    """Convert an image-level distance into a calibrated confidence-like score."""
    threshold = float(stats["image_score_threshold"])
    scale = max(float(stats["image_score_scale"]), 1e-4)

    z = np.clip((raw_score - threshold) / scale, -60.0, 60.0)
    return float(1.0 / (1.0 + np.exp(-z)))
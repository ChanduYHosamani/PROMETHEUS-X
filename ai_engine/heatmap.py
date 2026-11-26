"""Spatial anomaly map resizing, smoothing, transparent heatmap overlays, and defect localization."""

from typing import Dict, List, Tuple

import cv2
import numpy as np


def generate_anomaly_map(
    patch_scores: np.ndarray,
    spatial_shape: Tuple[int, int],
    target_size: Tuple[int, int],
    gaussian_sigma: float = 4.0,
) -> np.ndarray:
    """Reshape 1D patch scores to (H, W), resize to original image (W, H), and smooth.

    Args:
        patch_scores: 1D array of length H * W.
        spatial_shape: (H, W) of feature grid (e.g., (28, 28)).
        target_size: (orig_w, orig_h) of the original image.
        gaussian_sigma: Gaussian smoothing sigma in pixels.

    Returns:
        Float32 anomaly map of shape (orig_h, orig_w).
    """
    h_grid, w_grid = spatial_shape
    orig_w, orig_h = target_size
    grid_map = patch_scores.reshape(h_grid, w_grid).astype(np.float32)
    resized = cv2.resize(grid_map, (orig_w, orig_h), interpolation=cv2.INTER_CUBIC)
    if gaussian_sigma > 0:
        resized = cv2.GaussianBlur(resized, ksize=(0, 0), sigmaX=gaussian_sigma, sigmaY=gaussian_sigma)
    return resized


def normalize_anomaly_map(
    anomaly_map: np.ndarray,
    min_val: float | None = None,
    max_val: float | None = None,
) -> np.ndarray:
    """Normalize an anomaly map to [0.0, 1.0] float32."""
    lo = float(anomaly_map.min()) if min_val is None else float(min_val)
    hi = float(anomaly_map.max()) if max_val is None else float(max_val)
    denom = max(hi - lo, 1e-8)
    norm = np.clip((anomaly_map - lo) / denom, 0.0, 1.0)
    return norm.astype(np.float32)


def create_heatmap_overlay(
    original_rgb: np.ndarray,
    normalized_map: np.ndarray,
    alpha: float = 0.45,
) -> Tuple[np.ndarray, bytes]:
    """Generate a transparent heatmap overlay preserving the original RGB image.

    Returns:
        overlay_rgb: uint8 RGB image of shape (H, W, 3)
        png_bytes: PNG-encoded bytes of the overlay image
    """
    if original_rgb.shape[:2] != normalized_map.shape[:2]:
        raise ValueError(
            f"Shape mismatch: original_rgb={original_rgb.shape[:2]} vs normalized_map={normalized_map.shape[:2]}"
        )

    heat_uint8 = np.clip(normalized_map * 255.0, 0, 255).astype(np.uint8)
    heatmap_bgr = cv2.applyColorMap(heat_uint8, cv2.COLORMAP_JET)
    heatmap_rgb = cv2.cvtColor(heatmap_bgr, cv2.COLOR_BGR2RGB)

    overlay_rgb = cv2.addWeighted(original_rgb, 1.0 - alpha, heatmap_rgb, alpha, 0.0)
    overlay_bgr = cv2.cvtColor(overlay_rgb, cv2.COLOR_RGB2BGR)
    ok, buf = cv2.imencode(".png", overlay_bgr)
    if not ok:
        raise RuntimeError("Failed to encode heatmap overlay to PNG.")
    return overlay_rgb, buf.tobytes()


def extract_defect_regions(
    normalized_map: np.ndarray,
    threshold: float = 0.55,
    min_area_ratio: float = 0.001,
) -> List[Dict[str, float]]:
    """Extract normalized [0, 1] bounding boxes for localized defect regions."""
    h, w = normalized_map.shape
    total_area = float(h * w)
    binary_mask = (normalized_map >= threshold).astype(np.uint8)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_mask, connectivity=8)

    detections: List[Dict[str, float]] = []
    for label_idx in range(1, num_labels):
        x, y, bw, bh, area = stats[label_idx]
        area_ratio = float(area) / total_area
        if area_ratio < min_area_ratio:
            continue
        region_mask = labels == label_idx
        peak_score = float(normalized_map[region_mask].max())
        detections.append(
            {
                "bbox_x": float(x) / float(w),
                "bbox_y": float(y) / float(h),
                "bbox_w": float(bw) / float(w),
                "bbox_h": float(bh) / float(h),
                "area_ratio": area_ratio,
                "peak_score": peak_score,
            }
        )

    detections.sort(key=lambda d: d["peak_score"], reverse=True)
    return detections

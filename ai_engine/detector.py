"""PatchCore-inspired anomaly detector & inference pipeline."""

import time
from pathlib import Path
from typing import Dict, Union

import numpy as np
from PIL import Image
import torch

from ai_engine.backbone import ResNet18FeatureExtractor, resolve_device
from ai_engine.calibration import (
    classify_severity,
    normalize_calibrated_score,
)
from ai_engine.config import AIEngineConfig
from ai_engine.heatmap import (
    create_heatmap_overlay,
    extract_defect_regions,
    generate_anomaly_map,
    normalize_anomaly_map,
)
from ai_engine.memory_bank import CategoryMemoryBankManager, MemoryBankArtifact
from dataset_utils.mvtec_categories import MVTEC_CATEGORY_MAP
from dataset_utils.transforms import preprocess_image


@torch.inference_mode()
def compute_patch_nearest_neighbor_distances(
    query_embeddings: torch.Tensor,
    memory_bank: torch.Tensor,
    chunk_size: int = 2048,
) -> torch.Tensor:
    """Compute minimum Euclidean distance from each query patch to the memory bank.

    Processes the memory bank in chunks to prevent VRAM spikes on 4GB GPUs.
    Args:
        query_embeddings: Tensor of shape (N_patches, D)
        memory_bank: Tensor of shape (M_bank, D)
    Returns:
        min_distances: Float32 Tensor of shape (N_patches,)
    """
    q = query_embeddings.float()
    m = memory_bank.to(q.device, dtype=torch.float32)

    min_dists = torch.full(
        (q.shape[0],),
        float("inf"),
        device=q.device,
        dtype=torch.float32,
    )

    for start in range(0, m.shape[0], chunk_size):
        chunk = m[start : start + chunk_size]
        dists = torch.cdist(q, chunk, p=2)
        chunk_min, _ = dists.min(dim=1)
        min_dists = torch.minimum(min_dists, chunk_min)

    return min_dists


class PatchCoreDetector:
    """Coordinates ResNet18 feature extraction, k-NN scoring, and heatmap generation."""

    def __init__(self, config: AIEngineConfig | None = None) -> None:
        self.config = config or AIEngineConfig()
        self.device = resolve_device(self.config.device)
        self.backbone = ResNet18FeatureExtractor(self.config)
        self.memory_banks = CategoryMemoryBankManager(self.config)

    def load_models(self, pretrained: bool = True) -> None:
        """Eagerly load the ResNet18 feature extractor onto the configured device."""
        self.backbone.load(pretrained=pretrained)

    def predict(
        self,
        image_input: Union[bytes, Path, str, Image.Image],
        category_id: str,
        heatmap_alpha: float = 0.45,
        defect_threshold: float = 0.55,
    ) -> Dict[str, object]:
        """Run end-to-end anomaly detection and heatmap generation on one image."""
        if category_id not in MVTEC_CATEGORY_MAP:
            raise ValueError(f"Unknown MVTec AD category: '{category_id}'")

        t0 = time.perf_counter()

        if not self.backbone.is_loaded:
            self.backbone.load(pretrained=True)

        artifact: MemoryBankArtifact = self.memory_banks.load_category(category_id)

        tensor_1chw, original_rgb, orig_size = preprocess_image(
            image_input,
            image_size=self.config.input_size,
        )

        embeddings, spatial_shape = self.backbone.extract_patch_embeddings(
            tensor_1chw
        )

        patch_distances = compute_patch_nearest_neighbor_distances(
            embeddings.squeeze(0),
            artifact.features,
        )

        patch_scores_np = patch_distances.detach().cpu().numpy()

        # Calculate image-level anomaly score.
        raw_image_score = float(patch_scores_np.max())

        # Use held-out normal-image calibration statistics.
        normalized_score = normalize_calibrated_score(
            raw_image_score,
            artifact.stats,
        )

        anomaly_threshold = float(
            artifact.stats["image_score_threshold"]
        )

        is_anomalous = raw_image_score >= anomaly_threshold
        severity = classify_severity(normalized_score)

        # Generate and normalize the spatial anomaly map.
        raw_map = generate_anomaly_map(
            patch_scores=patch_scores_np,
            spatial_shape=spatial_shape,
            target_size=orig_size,
        )

        norm_map = normalize_anomaly_map(
            raw_map,
            min_val=artifact.stats.get("p05"),
            max_val=artifact.stats.get("p99_plus_margin"),
        )

        # Generate heatmap overlay.
        _, heatmap_png_bytes = create_heatmap_overlay(
            original_rgb=original_rgb,
            normalized_map=norm_map,
            alpha=heatmap_alpha,
        )

        # Extract defect regions only when the image is anomalous.
        detections = (
            extract_defect_regions(
                norm_map,
                threshold=defect_threshold,
            )
            if is_anomalous
            else []
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "category_id": category_id,
            "is_anomalous": bool(is_anomalous),
            "anomaly_score": raw_image_score,
            "calibrated_confidence": normalized_score,
            "severity": severity,
            "image_size": {
                "width": orig_size[0],
                "height": orig_size[1],
            },
            "spatial_shape": {
                "height": spatial_shape[0],
                "width": spatial_shape[1],
            },
            "spatial_anomaly_map": norm_map,
            "heatmap_overlay_png": heatmap_png_bytes,
            "detections": detections,
            "inference_time_ms": round(elapsed_ms, 2),
        }

    @staticmethod
    def _normalize_image_score(
        raw_score: float,
        stats: Dict[str, float],
    ) -> float:
        """Legacy normalization helper retained for compatibility."""
        mean = float(stats.get("mean", 0.35))
        std = max(float(stats.get("std", 0.15)), 1e-4)
        z = (raw_score - (mean + 2.0 * std)) / (2.0 * std)
        return float(1.0 / (1.0 + np.exp(-z)))
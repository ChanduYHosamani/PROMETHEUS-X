"""Category-specific PatchCore memory-bank training and image-level calibration."""

from pathlib import Path
from typing import Dict, List
import random

import numpy as np
import torch
from torch.utils.data import DataLoader, Subset

from ai_engine.backbone import ResNet18FeatureExtractor
from ai_engine.calibration import calibrate_image_scores
from ai_engine.config import AIEngineConfig
from ai_engine.detector import compute_patch_nearest_neighbor_distances
from ai_engine.memory_bank import CategoryMemoryBankManager, greedy_coreset_subsample
from dataset_utils.mvtec_categories import MVTEC_CATEGORIES, MVTEC_CATEGORY_MAP
from dataset_utils.mvtec_loader import MVTecDataset


class MemoryBankTrainer:
    """Build category-specific memory banks using normal training images only."""

    def __init__(
        self,
        dataset_root: Path | str,
        config: AIEngineConfig | None = None,
    ) -> None:
        self.dataset_root = Path(dataset_root)
        self.config = config or AIEngineConfig()
        self.backbone = ResNet18FeatureExtractor(self.config)
        self.memory_banks = CategoryMemoryBankManager(self.config)

    def build_category_bank(
        self,
        category_id: str,
        batch_size: int = 16,
        num_workers: int = 0,
        pretrained: bool = True,
        resume: bool = True,
    ) -> Dict[str, object]:

        if category_id not in MVTEC_CATEGORY_MAP:
            raise ValueError(f"Unknown MVTec AD category: '{category_id}'")

        if resume and self.memory_banks.has_artifact(category_id):
            return {
                "category_id": category_id,
                "status": "skipped_existing",
                "artifact_path": str(
                    self.memory_banks.get_artifact_path(category_id)
                ),
            }

        dataset = MVTecDataset(
            root_dir=self.dataset_root,
            category_id=category_id,
            split="train",
            image_size=self.config.input_size,
        )

        total_images = len(dataset)

        if total_images < 2:
            raise RuntimeError(
                f"Category '{category_id}' needs at least 2 normal "
                "training images for separate training and calibration."
            )

        # Deterministic 80/20 split.
        indices = list(range(total_images))
        random.Random(42).shuffle(indices)

        calibration_count = max(1, round(total_images * 0.20))
        calibration_count = min(calibration_count, total_images - 1)

        calibration_indices = indices[:calibration_count]
        training_indices = indices[calibration_count:]

        training_dataset = Subset(dataset, training_indices)
        calibration_dataset = Subset(dataset, calibration_indices)

        if not self.backbone.is_loaded:
            self.backbone.load(pretrained=pretrained)

        training_loader = DataLoader(
            training_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
        )

        all_patches: List[torch.Tensor] = []
        spatial_shape = (28, 28)

        # Build memory bank from training images only.
        for batch in training_loader:
            embeddings, spatial_shape = self.backbone.extract_patch_embeddings(
                batch["image"]
            )
            all_patches.append(
                embeddings.reshape(-1, embeddings.shape[-1]).cpu()
            )

        raw_bank = torch.cat(all_patches, dim=0)

        coreset_bank = greedy_coreset_subsample(
            raw_bank,
            ratio=self.config.coreset_sampling_ratio,
            device=self.backbone.device,
        )

        # Preserve patch-level statistics for anomaly-map normalization.
        sample_count = min(raw_bank.shape[0], 4096)
        sample_patches = raw_bank[:sample_count].to(self.backbone.device)

        patch_distances = compute_patch_nearest_neighbor_distances(
            sample_patches,
            coreset_bank.to(self.backbone.device),
        ).cpu().numpy()

        stats = {
            "mean": float(np.mean(patch_distances)),
            "std": float(np.std(patch_distances)),
            "p05": float(np.percentile(patch_distances, 5)),
            "p95": float(np.percentile(patch_distances, 95)),
            "p99": float(np.percentile(patch_distances, 99)),
            "p99_plus_margin": float(
                np.percentile(patch_distances, 99) * 1.5
            ),
        }

        # Calibrate using held-out normal images.
        calibration_loader = DataLoader(
            calibration_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
        )

        image_scores: List[float] = []

        for batch in calibration_loader:
            embeddings, _ = self.backbone.extract_patch_embeddings(
                batch["image"]
            )

            for image_embeddings in embeddings:
                distances = compute_patch_nearest_neighbor_distances(
                    image_embeddings,
                    coreset_bank.to(self.backbone.device),
                )
                image_scores.append(float(distances.max().cpu().item()))

        calibration_stats = calibrate_image_scores(image_scores)
        stats.update(calibration_stats)

        metadata = {
            "backbone_name": self.config.backbone_name,
            "feature_layers": list(self.config.feature_layers),
            "input_size": self.config.input_size,
            "coreset_sampling_ratio": self.config.coreset_sampling_ratio,
            "num_train_images": len(training_dataset),
            "num_calibration_images": len(calibration_dataset),
            "num_total_normal_images": total_images,
            "num_patches_raw": int(raw_bank.shape[0]),
            "calibration_seed": 42,
        }

        artifact_path = self.memory_banks.save_category(
            category_id=category_id,
            features=coreset_bank,
            spatial_shape=spatial_shape,
            stats=stats,
            metadata=metadata,
        )

        return {
            "category_id": category_id,
            "status": "built",
            "num_train_images": len(training_dataset),
            "num_calibration_images": len(calibration_dataset),
            "num_patches_raw": int(raw_bank.shape[0]),
            "num_patches_coreset": int(coreset_bank.shape[0]),
            "image_score_threshold": calibration_stats[
                "image_score_threshold"
            ],
            "artifact_path": str(artifact_path),
        }

    def build_all_categories(
        self,
        batch_size: int = 16,
        num_workers: int = 0,
        pretrained: bool = True,
        resume: bool = True,
    ) -> List[Dict[str, object]]:

        results = []

        for category in MVTEC_CATEGORIES:
            results.append(
                self.build_category_bank(
                    category_id=category.id,
                    batch_size=batch_size,
                    num_workers=num_workers,
                    pretrained=pretrained,
                    resume=resume,
                )
            )

        return results
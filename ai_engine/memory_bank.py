"""Category-specific normal feature memory bank manager with coreset reduction & LRU VRAM cache."""

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional

import torch

from ai_engine.backbone import resolve_device
from ai_engine.config import AIEngineConfig


@dataclass
class MemoryBankArtifact:
    category_id: str
    features: torch.Tensor  # (M, D)
    spatial_shape: tuple[int, int]
    stats: Dict[str, float]
    metadata: Dict[str, Any]


@torch.inference_mode()
def greedy_coreset_subsample(
    features: torch.Tensor,
    ratio: float = 0.1,
    max_samples: int = 10000,
    seed: int = 42,
    device: Optional[torch.device] = None,
) -> torch.Tensor:
    """Build a memory-efficient, deterministic approximate coreset.

    Small banks use exact greedy selection. Large banks use a deterministic
    candidate pool to reduce computation and GPU memory requirements.
    """
    n = features.shape[0]
    if n == 0:
        raise ValueError("Cannot subsample an empty feature tensor.")

    target_k = max(1, min(int(round(n * ratio)), max_samples, n))
    if target_k >= n:
        return features.clone()

    large_bank_threshold = 20000
    candidate_limit = 8192
    large_bank_output_limit = 2048

    gen = torch.Generator(device="cpu").manual_seed(seed)

    if n > large_bank_threshold:
        candidate_count = min(n, candidate_limit)
        candidate_indices = torch.randperm(n, generator=gen)[:candidate_count]
        candidates = features.index_select(0, candidate_indices)
        target_k = min(target_k, large_bank_output_limit)
    else:
        candidates = features

    compute_device = device or features.device
    feats = candidates.to(compute_device, dtype=torch.float32)
    candidate_n = feats.shape[0]

    if target_k >= candidate_n:
        return feats.cpu()

    start_idx = int(torch.randint(0, candidate_n, (1,), generator=gen).item())

    selected_indices = [start_idx]
    min_dists = torch.full(
        (candidate_n,), float("inf"),
        device=compute_device,
        dtype=torch.float32,
    )
    last_selected = feats[start_idx : start_idx + 1]

    for _ in range(1, target_k):
        dists = torch.cdist(feats, last_selected, p=2).squeeze(1)
        min_dists = torch.minimum(min_dists, dists)
        next_idx = int(torch.argmax(min_dists).item())
        selected_indices.append(next_idx)
        last_selected = feats[next_idx : next_idx + 1]

    idx_tensor = torch.tensor(
        selected_indices, dtype=torch.long, device=compute_device
    )
    return feats.index_select(0, idx_tensor).cpu()


class CategoryMemoryBankManager:
    """Manages per-category normal feature memory banks with 4GB VRAM LRU eviction."""

    def __init__(self, config: AIEngineConfig | None = None) -> None:
        self.config = config or AIEngineConfig()
        self.device = resolve_device(self.config.device)
        self._cache: OrderedDict[str, MemoryBankArtifact] = OrderedDict()

    def get_artifact_path(self, category_id: str) -> Path:
        return self.config.artifacts_dir / f"{category_id}_memory_bank.pt"

    def get_metadata_path(self, category_id: str) -> Path:
        return self.config.artifacts_dir / f"{category_id}_metadata.json"

    def has_artifact(self, category_id: str) -> bool:
        return self.get_artifact_path(category_id).exists()

    def save_category(
        self,
        category_id: str,
        features: torch.Tensor,
        spatial_shape: tuple[int, int],
        stats: Dict[str, float],
        metadata: Dict[str, Any],
    ) -> Path:
        """Persist a category memory bank (.pt) and human-readable metadata (.json)."""
        self.config.artifacts_dir.mkdir(parents=True, exist_ok=True)
        tensor_to_save = features.half().cpu() if self.config.use_fp16 else features.float().cpu()
        artifact_path = self.get_artifact_path(category_id)
        metadata_path = self.get_metadata_path(category_id)

        full_meta = {
            **metadata,
            "category_id": category_id,
            "feature_dim": int(tensor_to_save.shape[1]),
            "num_patches_coreset": int(tensor_to_save.shape[0]),
            "spatial_shape": list(spatial_shape),
            "stats": stats,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }

        torch.save(
            {
                "category_id": category_id,
                "features": tensor_to_save,
                "spatial_shape": spatial_shape,
                "stats": stats,
                "metadata": full_meta,
            },
            artifact_path,
        )
        metadata_path.write_text(json.dumps(full_meta, indent=2), encoding="utf-8")
        return artifact_path

    def load_category(self, category_id: str) -> MemoryBankArtifact:
        """Load a category memory bank into target device with LRU eviction."""
        if category_id in self._cache:
            self._cache.move_to_end(category_id)
            return self._cache[category_id]

        artifact_path = self.get_artifact_path(category_id)
        if not artifact_path.exists():
            raise FileNotFoundError(
                f"Memory bank for category '{category_id}' not found at {artifact_path}. "
                "Build category memory banks first."
            )

        payload = torch.load(artifact_path, map_location="cpu", weights_only=True)
        features = payload["features"].to(self.device)
        if self.device.type == "cuda" and self.config.use_fp16:
            features = features.half()
        else:
            features = features.float()

        artifact = MemoryBankArtifact(
            category_id=category_id,
            features=features,
            spatial_shape=tuple(payload["spatial_shape"]),
            stats=dict(payload.get("stats", {})),
            metadata=dict(payload.get("metadata", {})),
        )

        self._cache[category_id] = artifact
        self._evict_if_needed()
        return artifact

    def _evict_if_needed(self) -> None:
        max_banks = max(1, self.config.max_cached_banks_in_vram)
        evicted = False
        while len(self._cache) > max_banks:
            _, old_artifact = self._cache.popitem(last=False)
            del old_artifact
            evicted = True
        if evicted and self.device.type == "cuda":
            torch.cuda.empty_cache()

    def clear_cache(self) -> None:
        self._cache.clear()
        if self.device.type == "cuda":
            torch.cuda.empty_cache()










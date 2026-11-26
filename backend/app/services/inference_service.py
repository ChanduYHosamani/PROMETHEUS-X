"""Inference and model management service wrapping the isolated ai_engine package."""

import asyncio
from functools import lru_cache
from typing import Any, Dict

import anyio
import torch

from ai_engine.config import AIEngineConfig
from ai_engine.detector import PatchCoreDetector
from backend.app.core.config import get_settings
from dataset_utils.mvtec_categories import MVTEC_CATEGORIES, MVTEC_CATEGORY_MAP


class MemoryBankUnavailableError(FileNotFoundError):
    """Raised when a requested category's normal memory bank artifact is not built yet."""


class InferenceService:
    """Manages AI engine lifecycle, model readiness, and VRAM-safe inference execution."""

    def __init__(self) -> None:
        settings = get_settings()
        self.config = AIEngineConfig(
            device=settings.ai_device,
            use_fp16=settings.ai_use_fp16,
            max_cached_banks_in_vram=settings.ai_max_cached_banks,
        )
        self.detector = PatchCoreDetector(self.config)
        self._gpu_lock = asyncio.Lock()

    def has_memory_bank(self, category_id: str) -> bool:
        return self.detector.memory_banks.has_artifact(category_id)

    def load_category_bank(self, category_id: str) -> Dict[str, Any]:
        if category_id not in MVTEC_CATEGORY_MAP:
            raise ValueError(f"Unknown MVTec AD category: '{category_id}'")
        if not self.has_memory_bank(category_id):
            raise MemoryBankUnavailableError(
                f"Memory bank for category '{category_id}' is not available. "
                "Build category memory banks before running inference."
            )
        artifact = self.detector.memory_banks.load_category(category_id)
        return {
            "category_id": category_id,
            "loaded": True,
            "num_patches": int(artifact.features.shape[0]),
            "feature_dim": int(artifact.features.shape[1]),
        }

    def get_model_readiness(self) -> Dict[str, Any]:
        cuda_ok = torch.cuda.is_available()
        vram_total_mb = None
        vram_allocated_mb = None
        gpu_name = None
        if cuda_ok:
            props = torch.cuda.get_device_properties(0)
            gpu_name = props.name
            vram_total_mb = round(props.total_memory / (1024 * 1024), 1)
            vram_allocated_mb = round(torch.cuda.memory_allocated(0) / (1024 * 1024), 1)

        ready_categories = [c.id for c in MVTEC_CATEGORIES if self.has_memory_bank(c.id)]
        return {
            "backbone_name": self.config.backbone_name,
            "backbone_loaded": self.detector.backbone.is_loaded,
            "device": str(self.detector.device),
            "use_fp16": self.detector.backbone.use_fp16,
            "cuda_available": cuda_ok,
            "gpu_name": gpu_name,
            "vram_total_mb": vram_total_mb,
            "vram_allocated_mb": vram_allocated_mb,
            "max_cached_banks_in_vram": self.config.max_cached_banks_in_vram,
            "cached_categories": list(self.detector.memory_banks._cache.keys()),
            "ready_categories": ready_categories,
            "ready_count": len(ready_categories),
            "total_categories": len(MVTEC_CATEGORIES),
        }

    async def predict(self, image_bytes: bytes, category_id: str) -> Dict[str, Any]:
        if category_id not in MVTEC_CATEGORY_MAP:
            raise ValueError(f"Unknown MVTec AD category: '{category_id}'")
        if not self.has_memory_bank(category_id):
            raise MemoryBankUnavailableError(
                f"Memory bank for category '{category_id}' is not available. "
                "Build category memory banks before running inference."
            )

        async with self._gpu_lock:
            return await anyio.to_thread.run_sync(self.detector.predict, image_bytes, category_id)


@lru_cache
def get_inference_service() -> InferenceService:
    return InferenceService()

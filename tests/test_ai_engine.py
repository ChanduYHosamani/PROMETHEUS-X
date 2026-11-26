"""Phase 2 verification tests for AI engine, dataset loader, memory bank, and heatmap pipeline."""

from io import BytesIO
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image
import torch

from ai_engine.backbone import ResNet18FeatureExtractor
from ai_engine.config import AIEngineConfig
from ai_engine.detector import PatchCoreDetector
from ai_engine.memory_bank import CategoryMemoryBankManager, greedy_coreset_subsample
from ai_engine.trainer import MemoryBankTrainer
from dataset_utils.mvtec_loader import MVTecDataset


def _save_dummy_png(path: Path, size: tuple[int, int] = (320, 240), value: int = 128) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    arr = np.full((size[1], size[0], 3), value, dtype=np.uint8)
    Image.fromarray(arr).save(path, format="PNG")


def test_resnet18_layer2_layer3_feature_shapes() -> None:
    cfg = AIEngineConfig(device="cuda" if torch.cuda.is_available() else "cpu", use_fp16=True)
    extractor = ResNet18FeatureExtractor(cfg)
    extractor.load(pretrained=False)

    dummy = torch.randn(2, 3, 224, 224)
    embeddings, spatial_hw = extractor.extract_patch_embeddings(dummy)
    assert spatial_hw == (28, 28)
    assert embeddings.shape == (2, 784, 384)
    norms = torch.linalg.norm(embeddings, dim=-1)
    assert torch.allclose(norms, torch.ones_like(norms), atol=1e-3)


def test_coreset_and_lru_memory_bank_manager() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg = AIEngineConfig(
            device="cuda" if torch.cuda.is_available() else "cpu",
            max_cached_banks_in_vram=2,
            artifacts_dir=Path(tmp),
        )
        manager = CategoryMemoryBankManager(cfg)
        raw = torch.randn(500, 384)
        coreset = greedy_coreset_subsample(raw, ratio=0.1)
        assert coreset.shape == (50, 384)

        for cat in ("bottle", "cable", "carpet"):
            manager.save_category(
                category_id=cat,
                features=coreset,
                spatial_shape=(28, 28),
                stats={"mean": 0.3, "std": 0.1},
                metadata={"test": True},
            )
            assert manager.has_artifact(cat)

        manager.load_category("bottle")
        manager.load_category("cable")
        manager.load_category("carpet")
        assert list(manager._cache.keys()) == ["cable", "carpet"]


def test_mvtec_loader_trainer_and_inference_end_to_end() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "mvtec"
        artifacts = Path(tmp) / "artifacts"

        # Create synthetic train/good (2 images) and test/good + test/crack + ground_truth
        _save_dummy_png(root / "bottle" / "train" / "good" / "000.png", size=(300, 200), value=100)
        _save_dummy_png(root / "bottle" / "train" / "good" / "001.png", size=(300, 200), value=105)
        _save_dummy_png(root / "bottle" / "test" / "good" / "000.png", size=(300, 200), value=102)
        _save_dummy_png(root / "bottle" / "test" / "crack" / "001.png", size=(300, 200), value=240)
        mask_path = root / "bottle" / "ground_truth" / "crack" / "001_mask.png"
        mask_path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(np.full((200, 300), 255, dtype=np.uint8)).save(mask_path)

        train_ds = MVTecDataset(root, "bottle", split="train")
        test_ds = MVTecDataset(root, "bottle", split="test")
        assert len(train_ds) == 2
        assert all(s.split == "train" and not s.is_anomalous for s in train_ds.samples)
        assert len(test_ds) == 2
        assert sum(1 for s in test_ds.samples if s.is_anomalous) == 1

        cfg = AIEngineConfig(
            device="cuda" if torch.cuda.is_available() else "cpu",
            coreset_sampling_ratio=0.1,
            artifacts_dir=artifacts,
        )
        trainer = MemoryBankTrainer(root, cfg)
        build_res = trainer.build_category_bank("bottle", batch_size=2, pretrained=False, resume=True)
        assert build_res["status"] == "built"

        resume_res = trainer.build_category_bank("bottle", batch_size=2, pretrained=False, resume=True)
        assert resume_res["status"] == "skipped_existing"

        detector = PatchCoreDetector(cfg)
        detector.load_models(pretrained=False)
        buf = BytesIO()
        Image.fromarray(np.full((200, 300, 3), 220, dtype=np.uint8)).save(buf, format="PNG")
        pred = detector.predict(buf.getvalue(), "bottle")

        assert pred["category_id"] == "bottle"
        assert pred["image_size"] == {"width": 300, "height": 200}
        assert pred["spatial_anomaly_map"].shape == (200, 300)
        assert isinstance(pred["heatmap_overlay_png"], bytes) and len(pred["heatmap_overlay_png"]) > 100
        assert pred["severity"] in {"low", "medium", "high", "critical"}

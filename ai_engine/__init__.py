"""AI/ML Engine package for PROMETHEUS-X (ResNet18 + PatchCore-inspired)."""

from ai_engine.backbone import ResNet18FeatureExtractor
from ai_engine.calibration import SeverityThresholds, classify_severity
from ai_engine.config import AIEngineConfig
from ai_engine.detector import PatchCoreDetector
from ai_engine.heatmap import (
    create_heatmap_overlay,
    extract_defect_regions,
    generate_anomaly_map,
    normalize_anomaly_map,
)
from ai_engine.memory_bank import CategoryMemoryBankManager, greedy_coreset_subsample
from ai_engine.trainer import MemoryBankTrainer

__all__ = [
    "AIEngineConfig",
    "CategoryMemoryBankManager",
    "MemoryBankTrainer",
    "PatchCoreDetector",
    "ResNet18FeatureExtractor",
    "SeverityThresholds",
    "classify_severity",
    "create_heatmap_overlay",
    "extract_defect_regions",
    "generate_anomaly_map",
    "greedy_coreset_subsample",
    "normalize_anomaly_map",
]

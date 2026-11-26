"""AI Engine configuration tuned for Windows + NVIDIA RTX 3050 4GB VRAM."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple


@dataclass
class AIEngineConfig:
    backbone_name: str = "resnet18"
    feature_layers: Tuple[str, ...] = ("layer2", "layer3")
    input_size: int = 224
    use_fp16: bool = True
    device: str = "cuda"
    max_cached_banks_in_vram: int = 2
    coreset_sampling_ratio: float = 0.1
    knn_neighbors: int = 9
    artifacts_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent / "artifacts")

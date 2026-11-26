"""ResNet18 pretrained feature extractor (Layer2 & Layer3) for PatchCore."""

from typing import Dict, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models import ResNet18_Weights, resnet18

from ai_engine.config import AIEngineConfig


def resolve_device(requested_device: str) -> torch.device:
    """Resolve 'cuda' or 'cpu' safely, falling back to CPU if CUDA is unavailable."""
    if requested_device.startswith("cuda") and torch.cuda.is_available():
        return torch.device(requested_device)
    return torch.device("cpu")


class ResNet18FeatureExtractor:
    """Extracts multi-scale intermediate feature maps from ResNet18 Layer2 and Layer3."""

    def __init__(self, config: AIEngineConfig | None = None) -> None:
        self.config = config or AIEngineConfig()
        self.device = resolve_device(self.config.device)
        self.use_fp16 = bool(self.config.use_fp16 and self.device.type == "cuda")
        self.model: nn.Module | None = None
        self._features: Dict[str, torch.Tensor] = {}
        self._hook_handles: list = []
        self.is_loaded = False

    def load(self, pretrained: bool = True) -> None:
        """Load ResNet18 backbone onto target device and register Layer2/Layer3 hooks."""
        if self.is_loaded and self.model is not None:
            return

        weights = ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
        model = resnet18(weights=weights)
        model.eval()
        for param in model.parameters():
            param.requires_grad_(False)

        self._clear_hooks()
        layer_map = {"layer1": model.layer1, "layer2": model.layer2, "layer3": model.layer3, "layer4": model.layer4}
        for layer_name in self.config.feature_layers:
            if layer_name not in layer_map:
                raise ValueError(f"Unsupported ResNet18 layer: {layer_name}")
            handle = layer_map[layer_name].register_forward_hook(self._make_hook(layer_name))
            self._hook_handles.append(handle)

        model.to(self.device)
        if self.use_fp16:
            model.half()

        self.model = model
        self.is_loaded = True

    def _make_hook(self, name: str):
        def hook(_module: nn.Module, _inputs: tuple, output: torch.Tensor) -> None:
            self._features[name] = output

        return hook

    def _clear_hooks(self) -> None:
        for h in self._hook_handles:
            h.remove()
        self._hook_handles.clear()

    @torch.inference_mode()
    def extract_patch_embeddings(self, images: torch.Tensor) -> Tuple[torch.Tensor, Tuple[int, int]]:
        """Extract L2-normalized multi-scale patch embeddings from a batch of images.

        Args:
            images: Tensor of shape (B, 3, 224, 224).

        Returns:
            embeddings: Tensor of shape (B, H*W, C_total) where C_total = 128 + 256 = 384.
            spatial_shape: (H, W) of the reference feature grid (28, 28 for 224x224 input).
        """
        if not self.is_loaded or self.model is None:
            self.load(pretrained=True)

        self._features.clear()
        x = images.to(self.device, non_blocking=True)
        if self.use_fp16:
            x = x.half()

        _ = self.model(x)

        aligned_maps = []
        target_hw: Tuple[int, int] | None = None

        for idx, layer_name in enumerate(self.config.feature_layers):
            fmap = self._features[layer_name]
            fmap = F.avg_pool2d(fmap, kernel_size=3, stride=1, padding=1)
            if idx == 0:
                target_hw = (fmap.shape[-2], fmap.shape[-1])
            elif (fmap.shape[-2], fmap.shape[-1]) != target_hw:
                fmap = F.interpolate(fmap, size=target_hw, mode="bilinear", align_corners=False)
            aligned_maps.append(fmap)

        self._features.clear()
        assert target_hw is not None

        concat = torch.cat(aligned_maps, dim=1)
        b, c, h, w = concat.shape
        embeddings = concat.permute(0, 2, 3, 1).reshape(b, h * w, c)
        embeddings = F.normalize(embeddings.float(), p=2, dim=-1)
        return embeddings, target_hw

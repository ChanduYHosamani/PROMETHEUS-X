"""Image preprocessing and normalization transforms for ResNet18 + PatchCore."""

from io import BytesIO
from pathlib import Path
from typing import Tuple, Union

import numpy as np
from PIL import Image
import torch
from torchvision import transforms

IMAGENET_MEAN: Tuple[float, float, float] = (0.485, 0.456, 0.406)
IMAGENET_STD: Tuple[float, float, float] = (0.229, 0.224, 0.225)
DEFAULT_IMAGE_SIZE: int = 224
DEFAULT_RESIZE_SIZE: int = 256


def get_inference_transform_spec(image_size: int = DEFAULT_IMAGE_SIZE) -> dict:
    """Return deterministic preprocessing specification."""
    return {
        "resize": (DEFAULT_RESIZE_SIZE, DEFAULT_RESIZE_SIZE),
        "center_crop": (image_size, image_size),
        "normalize_mean": IMAGENET_MEAN,
        "normalize_std": IMAGENET_STD,
    }


def build_image_transform(
    image_size: int = DEFAULT_IMAGE_SIZE,
    resize_size: int = DEFAULT_RESIZE_SIZE,
) -> transforms.Compose:
    """Build deterministic torchvision preprocessing pipeline for RGB images."""
    return transforms.Compose(
        [
            transforms.Resize((resize_size, resize_size), interpolation=transforms.InterpolationMode.BILINEAR),
            transforms.CenterCrop((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ]
    )


def build_mask_transform(
    image_size: int = DEFAULT_IMAGE_SIZE,
    resize_size: int = DEFAULT_RESIZE_SIZE,
) -> transforms.Compose:
    """Build deterministic preprocessing pipeline for binary ground-truth masks."""
    return transforms.Compose(
        [
            transforms.Resize((resize_size, resize_size), interpolation=transforms.InterpolationMode.NEAREST),
            transforms.CenterCrop((image_size, image_size)),
            transforms.ToTensor(),
        ]
    )


def load_rgb_image(image_input: Union[bytes, Path, str, Image.Image]) -> Image.Image:
    """Load an image from bytes, file path, or PIL Image and convert to RGB."""
    if isinstance(image_input, Image.Image):
        return image_input.convert("RGB")
    if isinstance(image_input, (Path, str)):
        with Image.open(image_input) as img:
            return img.convert("RGB")
    if isinstance(image_input, (bytes, bytearray)):
        with Image.open(BytesIO(image_input)) as img:
            return img.convert("RGB")
    raise TypeError(f"Unsupported image input type: {type(image_input).__name__}")


def preprocess_image(
    image_input: Union[bytes, Path, str, Image.Image],
    image_size: int = DEFAULT_IMAGE_SIZE,
) -> Tuple[torch.Tensor, np.ndarray, Tuple[int, int]]:
    """Preprocess an input image for ResNet18 inference.

    Returns:
        tensor_1chw: FloatTensor of shape (1, 3, image_size, image_size)
        original_rgb: uint8 numpy array of shape (orig_h, orig_w, 3)
        original_size: (orig_w, orig_h)
    """
    pil_img = load_rgb_image(image_input)
    orig_w, orig_h = pil_img.size
    original_rgb = np.array(pil_img, dtype=np.uint8)
    transform = build_image_transform(image_size=image_size)
    tensor_1chw = transform(pil_img).unsqueeze(0)
    return tensor_1chw, original_rgb, (orig_w, orig_h)

"""MVTec AD dataset loader supporting all 15 categories with strict train/test separation."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal, Optional

from PIL import Image
import torch
from torch.utils.data import Dataset

from dataset_utils.mvtec_categories import MVTEC_CATEGORIES, MVTEC_CATEGORY_MAP
from dataset_utils.transforms import DEFAULT_IMAGE_SIZE, build_image_transform, build_mask_transform

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


@dataclass(frozen=True)
class MVTecSample:
    image_path: Path
    category_id: str
    split: Literal["train", "test"]
    defect_type: str
    is_anomalous: bool
    mask_path: Optional[Path] = None


def _is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def scan_mvtec_category(
    root_dir: Path | str,
    category_id: str,
    split: Literal["train", "test"],
) -> List[MVTecSample]:
    """Discover samples for a single MVTec AD category and split.

    Strictly enforces:
      - split='train': reads ONLY `<root>/<category>/train/good` (never test images).
      - split='test': reads `<root>/<category>/test/good` and all defect subfolders,
        pairing defective samples with `<root>/<category>/ground_truth/<defect>/<stem>_mask.png`.
    """
    if category_id not in MVTEC_CATEGORY_MAP:
        raise ValueError(f"Unknown MVTec AD category '{category_id}'. Must be one of {list(MVTEC_CATEGORY_MAP)}")

    cat_dir = Path(root_dir) / category_id
    if not cat_dir.exists():
        raise FileNotFoundError(f"Category directory not found: {cat_dir}")

    samples: List[MVTecSample] = []

    if split == "train":
        good_dir = cat_dir / "train" / "good"
        if not good_dir.exists():
            raise FileNotFoundError(f"Training 'good' directory not found: {good_dir}")
        for img_path in sorted(good_dir.iterdir()):
            if _is_image_file(img_path):
                samples.append(
                    MVTecSample(
                        image_path=img_path,
                        category_id=category_id,
                        split="train",
                        defect_type="good",
                        is_anomalous=False,
                        mask_path=None,
                    )
                )
        return samples

    if split == "test":
        test_dir = cat_dir / "test"
        if not test_dir.exists():
            raise FileNotFoundError(f"Test directory not found: {test_dir}")
        gt_dir = cat_dir / "ground_truth"

        for defect_dir in sorted(d for d in test_dir.iterdir() if d.is_dir()):
            defect_type = defect_dir.name
            is_anomalous = defect_type != "good"
            for img_path in sorted(defect_dir.iterdir()):
                if not _is_image_file(img_path):
                    continue
                mask_path: Optional[Path] = None
                if is_anomalous and gt_dir.exists():
                    candidate = gt_dir / defect_type / f"{img_path.stem}_mask.png"
                    if candidate.exists():
                        mask_path = candidate
                samples.append(
                    MVTecSample(
                        image_path=img_path,
                        category_id=category_id,
                        split="test",
                        defect_type=defect_type,
                        is_anomalous=is_anomalous,
                        mask_path=mask_path,
                    )
                )
        return samples

    raise ValueError(f"Invalid split '{split}'. Expected 'train' or 'test'.")


class MVTecDataset(Dataset):
    """PyTorch Dataset for MVTec AD train (normal-only) and test (normal + defect + GT mask)."""

    def __init__(
        self,
        root_dir: Path | str,
        category_id: str,
        split: Literal["train", "test"] = "train",
        image_size: int = DEFAULT_IMAGE_SIZE,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.category_id = category_id
        self.split = split
        self.image_size = image_size
        self.samples = scan_mvtec_category(self.root_dir, category_id, split)
        self.image_transform = build_image_transform(image_size=image_size)
        self.mask_transform = build_mask_transform(image_size=image_size)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, object]:
        sample = self.samples[idx]
        with Image.open(sample.image_path) as img:
            image_tensor = self.image_transform(img.convert("RGB"))

        if sample.mask_path is not None:
            with Image.open(sample.mask_path) as mask_img:
                mask_tensor = (self.mask_transform(mask_img.convert("L")) > 0.5).float()
        else:
            mask_tensor = torch.zeros((1, self.image_size, self.image_size), dtype=torch.float32)

        return {
            "image": image_tensor,
            "label": int(sample.is_anomalous),
            "mask": mask_tensor,
            "defect_type": sample.defect_type,
            "image_path": str(sample.image_path),
            "category_id": sample.category_id,
        }


def discover_available_categories(root_dir: Path | str) -> List[str]:
    """Return canonical MVTec AD category IDs present on disk under root_dir."""
    root = Path(root_dir)
    if not root.exists():
        return []
    return [cat.id for cat in MVTEC_CATEGORIES if (root / cat.id).is_dir()]

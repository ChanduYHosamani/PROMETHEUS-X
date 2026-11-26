"""Canonical MVTec AD dataset category definitions for PROMETHEUS-X."""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class MVTecCategory:
    id: str
    display_name: str
    domain_type: str  # "object" or "texture"
    default_input_size: int = 224


MVTEC_CATEGORIES: List[MVTecCategory] = [
    MVTecCategory("bottle", "Bottle", "object"),
    MVTecCategory("cable", "Cable", "object"),
    MVTecCategory("capsule", "Capsule", "object"),
    MVTecCategory("carpet", "Carpet", "texture"),
    MVTecCategory("grid", "Grid", "texture"),
    MVTecCategory("hazelnut", "Hazelnut", "object"),
    MVTecCategory("leather", "Leather", "texture"),
    MVTecCategory("metal_nut", "Metal Nut", "object"),
    MVTecCategory("pill", "Pill", "object"),
    MVTecCategory("screw", "Screw", "object"),
    MVTecCategory("tile", "Tile", "texture"),
    MVTecCategory("toothbrush", "Toothbrush", "object"),
    MVTecCategory("transistor", "Transistor", "object"),
    MVTecCategory("wood", "Wood", "texture"),
    MVTecCategory("zipper", "Zipper", "object"),
]

MVTEC_CATEGORY_MAP: Dict[str, MVTecCategory] = {c.id: c for c in MVTEC_CATEGORIES}

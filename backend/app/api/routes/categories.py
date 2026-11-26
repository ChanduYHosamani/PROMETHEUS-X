"""MVTec AD 15-category metadata endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.schemas.common import CategoryItem
from backend.app.services.inference_service import InferenceService, get_inference_service
from dataset_utils.mvtec_categories import MVTEC_CATEGORIES, MVTEC_CATEGORY_MAP

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=List[CategoryItem])
async def list_categories(
    inference: InferenceService = Depends(get_inference_service),
) -> List[CategoryItem]:
    return [
        CategoryItem(
            id=cat.id,
            display_name=cat.display_name,
            domain_type=cat.domain_type,
            default_input_size=cat.default_input_size,
            memory_bank_ready=inference.has_memory_bank(cat.id),
        )
        for cat in MVTEC_CATEGORIES
    ]


@router.get("/{category_id}", response_model=CategoryItem)
async def get_category(
    category_id: str,
    inference: InferenceService = Depends(get_inference_service),
) -> CategoryItem:
    cat = MVTEC_CATEGORY_MAP.get(category_id)
    if cat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown MVTec AD category: {category_id}",
        )
    return CategoryItem(
        id=cat.id,
        display_name=cat.display_name,
        domain_type=cat.domain_type,
        default_input_size=cat.default_input_size,
        memory_bank_ready=inference.has_memory_bank(cat.id),
    )

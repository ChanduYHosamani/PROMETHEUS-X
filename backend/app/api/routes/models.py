"""Model management and hardware readiness endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.services.inference_service import (
    InferenceService,
    MemoryBankUnavailableError,
    get_inference_service,
)

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/status")
async def get_models_status(
    inference: InferenceService = Depends(get_inference_service),
) -> dict:
    """Report backbone state, GPU/CPU device telemetry, and per-category bank readiness."""
    return inference.get_model_readiness()


@router.post("/{category_id}/load")
async def load_category_model(
    category_id: str,
    inference: InferenceService = Depends(get_inference_service),
) -> dict:
    """Preload a category memory bank into the VRAM LRU cache."""
    try:
        return inference.load_category_bank(category_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except MemoryBankUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

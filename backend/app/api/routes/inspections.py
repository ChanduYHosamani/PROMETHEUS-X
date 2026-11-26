"""Image inspection & persistent inspection history endpoints."""

import base64
from io import BytesIO
from typing import Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from PIL import Image, UnidentifiedImageError

from backend.app.core.config import get_settings
from backend.app.core.security import (
    AuthenticatedUser,
    get_current_user,
    get_optional_current_user,
)
from backend.app.schemas.inspection import (
    DefectRegionOut,
    InspectionDeleteOut,
    InspectionHistoryListOut,
    InspectionPredictOut,
)
from backend.app.services.inference_service import (
    InferenceService,
    MemoryBankUnavailableError,
    get_inference_service,
)
from backend.app.services.supabase_service import SupabaseService
from dataset_utils.mvtec_categories import MVTEC_CATEGORY_MAP

router = APIRouter(prefix="/inspections", tags=["inspections"])

ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/bmp",
    "image/tiff",
}


def get_supabase_service() -> SupabaseService:
    return SupabaseService()


def _validate_uploaded_image(file: UploadFile, raw_bytes: bytes, max_bytes: int) -> tuple[int, int]:
    if file.content_type and file.content_type.lower() not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image content type: {file.content_type}.",
        )
    if not raw_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image file is empty.",
        )
    if len(raw_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds maximum allowed size of {max_bytes // (1024 * 1024)} MB.",
        )
    try:
        with Image.open(BytesIO(raw_bytes)) as img:
            img.verify()
        with Image.open(BytesIO(raw_bytes)) as img2:
            return img2.size
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid or readable image.",
        ) from exc


@router.post("", response_model=InspectionPredictOut, status_code=status.HTTP_200_OK)
async def create_inspection(
    category_id: str = Form(...),
    source_type: Literal["upload", "camera"] = Form("upload"),
    file: UploadFile = File(...),
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_current_user),
    inference: InferenceService = Depends(get_inference_service),
    supabase: SupabaseService = Depends(get_supabase_service),
) -> InspectionPredictOut:
    """Validate uploaded image, run PatchCore inference, and persist to Supabase if configured."""
    if category_id not in MVTEC_CATEGORY_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown MVTec AD category: '{category_id}'.",
        )

    settings = get_settings()
    raw_bytes = await file.read()
    orig_w, orig_h = _validate_uploaded_image(file, raw_bytes, settings.max_upload_bytes)

    try:
        prediction = await inference.predict(raw_bytes, category_id)
    except MemoryBankUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    inspection_id = str(uuid4())
    heatmap_bytes: bytes = prediction["heatmap_overlay_png"]
    heatmap_b64 = base64.b64encode(heatmap_bytes).decode("ascii")
    detections = [DefectRegionOut(**d) for d in prediction["detections"]]

    persisted = False
    image_storage_path: Optional[str] = None
    heatmap_storage_path: Optional[str] = None

    if supabase.is_configured():
        ext = "png" if (file.content_type or "").endswith("png") else "jpg"
        owner_prefix = current_user.id if current_user else "anonymous"
        image_obj = f"{owner_prefix}/{inspection_id}/input.{ext}"
        heatmap_obj = f"{owner_prefix}/{inspection_id}/heatmap.png"

        image_storage_path = supabase.upload_storage_object(
            image_obj, raw_bytes, file.content_type or "image/jpeg"
        )
        heatmap_storage_path = supabase.upload_storage_object(
            heatmap_obj, heatmap_bytes, "image/png"
        )

        created = supabase.create_inspection_record(
            inspection_payload={
                "id": inspection_id,
                "user_id": current_user.id if current_user else None,
                "category_id": category_id,
                "source_type": source_type,
                "status": "completed",
                "image_storage_path": image_storage_path,
                "image_width": orig_w,
                "image_height": orig_h,
            },
            result_payload={
                "is_anomalous": prediction["is_anomalous"],
                "anomaly_score": prediction["anomaly_score"],
                "calibrated_confidence": prediction["calibrated_confidence"],
                "severity": prediction["severity"],
                "heatmap_storage_path": heatmap_storage_path,
                "inference_time_ms": prediction["inference_time_ms"],
            },
            detections_payload=prediction["detections"],
        )
        inspection_id = str(created["inspection"]["id"])
        persisted = True

    return InspectionPredictOut(
        inspection_id=inspection_id,
        category_id=category_id,
        source_type=source_type,
        status="completed",
        is_anomalous=prediction["is_anomalous"],
        anomaly_score=prediction["anomaly_score"],
        calibrated_confidence=prediction["calibrated_confidence"],
        severity=prediction["severity"],
        image_size=prediction["image_size"],
        heatmap_base64=heatmap_b64,
        heatmap_storage_path=heatmap_storage_path,
        image_storage_path=image_storage_path,
        detections=detections,
        inference_time_ms=prediction["inference_time_ms"],
        persisted_to_supabase=persisted,
    )


@router.get("", response_model=InspectionHistoryListOut)
async def list_inspections(
    category_id: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
) -> InspectionHistoryListOut:
    """List persisted inspection records for the authenticated user."""
    if category_id is not None and category_id not in MVTEC_CATEGORY_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown MVTec AD category: '{category_id}'.",
        )
    owner_filter = None if current_user.role == "admin" else current_user.id
    rows = supabase.list_inspections(
        user_id=owner_filter, category_id=category_id, limit=limit, offset=offset
    )
    return InspectionHistoryListOut(items=rows, count=len(rows), limit=limit, offset=offset)


@router.get("/{inspection_id}")
async def get_inspection(
    inspection_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
) -> dict:
    """Retrieve a single persisted inspection record."""
    owner_filter = None if current_user.role == "admin" else current_user.id
    row = supabase.get_inspection(inspection_id, user_id=owner_filter)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found.",
        )
    return row


@router.delete("/{inspection_id}", response_model=InspectionDeleteOut)
async def delete_inspection(
    inspection_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
) -> InspectionDeleteOut:
    """Delete a persisted inspection record owned by the authenticated user."""
    owner_filter = None if current_user.role == "admin" else current_user.id
    deleted = supabase.delete_inspection(inspection_id, user_id=owner_filter)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found.",
        )
    return InspectionDeleteOut(deleted=True, inspection_id=inspection_id)

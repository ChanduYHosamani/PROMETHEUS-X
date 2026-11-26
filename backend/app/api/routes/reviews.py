"""False-positive & human-in-the-loop review endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.core.security import AuthenticatedUser, get_current_user
from backend.app.schemas.review import ReviewCreateIn, ReviewListOut, ReviewOut
from backend.app.services.supabase_service import SupabaseService

router = APIRouter(prefix="/reviews", tags=["reviews"])


def get_supabase_service() -> SupabaseService:
    return SupabaseService()


@router.post("", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def create_review(
    payload: ReviewCreateIn,
    current_user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
) -> ReviewOut:
    """Persist an operator review for false-positive tracking."""
    owner_filter = None if current_user.role == "admin" else current_user.id
    inspection = supabase.get_inspection(str(payload.inspection_id), user_id=owner_filter)
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{payload.inspection_id}' not found.",
        )

    created = supabase.create_review(
        {
            "inspection_id": str(payload.inspection_id),
            "reviewer_id": current_user.id,
            "verdict": payload.verdict,
            "corrected_severity": payload.corrected_severity,
            "notes": payload.notes,
        }
    )
    return ReviewOut(**created)


@router.get("", response_model=ReviewListOut)
async def list_reviews(
    inspection_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
) -> ReviewListOut:
    """List operator review records from Supabase."""
    reviewer_filter = None if current_user.role == "admin" else current_user.id
    rows = supabase.list_reviews(
        inspection_id=inspection_id, reviewer_id=reviewer_filter, limit=limit
    )
    items = [ReviewOut(**r) for r in rows]
    return ReviewListOut(items=items, count=len(items))

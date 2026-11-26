"""Health and hardware readiness endpoints."""

import torch
from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.schemas.common import HealthResponse
from backend.app.services.supabase_service import SupabaseService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    cuda_ok = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if cuda_ok else None
    sb_status = SupabaseService().status()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        phase="phase-3-backend",
        cuda_available=cuda_ok,
        gpu_name=gpu_name,
        supabase_configured=sb_status.configured,
    )

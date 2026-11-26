"""Common API response schemas."""

from typing import Literal
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app: str
    version: str
    environment: str
    phase: str
    cuda_available: bool
    gpu_name: str | None
    supabase_configured: bool


class CategoryItem(BaseModel):
    id: str
    display_name: str
    domain_type: Literal["object", "texture"]
    default_input_size: int
    memory_bank_ready: bool

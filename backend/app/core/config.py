"""Application settings loaded securely from environment variables."""

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field

_BACKEND_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
_ROOT_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
print("Backend env path:", _BACKEND_ENV_PATH)
print("Backend env exists:", _BACKEND_ENV_PATH.exists())

# Load backend/.env first regardless of current working directory, then root .env as fallback.
load_dotenv(_BACKEND_ENV_PATH, override=False)
load_dotenv(_ROOT_ENV_PATH, override=False)


def _parse_cors_origins() -> List[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


class Settings(BaseModel):
    app_name: str = "PROMETHEUS-X API"
    app_version: str = "0.2.0"
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    api_v1_prefix: str = "/api/v1"
    cors_origins: List[str] = Field(default_factory=_parse_cors_origins)
    max_upload_bytes: int = Field(
        default_factory=lambda: int(os.getenv("MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))
    )

    # Supabase configuration (never hardcode real secrets)
    supabase_url: str = Field(default_factory=lambda: os.getenv("SUPABASE_URL", "").rstrip("/"))
    supabase_anon_key: str = Field(default_factory=lambda: os.getenv("SUPABASE_ANON_KEY", ""))
    supabase_service_role_key: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    )
    supabase_jwt_secret: str = Field(default_factory=lambda: os.getenv("SUPABASE_JWT_SECRET", ""))
    supabase_storage_bucket: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_STORAGE_BUCKET", "inspections")
    )

    # AI Engine / Hardware settings
    ai_device: str = Field(default_factory=lambda: os.getenv("AI_DEVICE", "cuda"))
    ai_use_fp16: bool = Field(
        default_factory=lambda: os.getenv("AI_USE_FP16", "true").lower() == "true"
    )
    ai_max_cached_banks: int = Field(
        default_factory=lambda: int(os.getenv("AI_MAX_CACHED_BANKS", "2"))
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

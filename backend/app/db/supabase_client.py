"""Supabase client factory & configuration status."""

from dataclasses import dataclass
from typing import Optional

from backend.app.core.config import Settings, get_settings


@dataclass
class SupabaseConfigStatus:
    configured: bool
    url_present: bool
    anon_key_present: bool
    service_role_present: bool
    jwt_secret_present: bool
    storage_bucket: str


def get_supabase_status(settings: Optional[Settings] = None) -> SupabaseConfigStatus:
    """Return non-secret configuration status for health/readiness checks."""
    cfg = settings or get_settings()
    url_ok = bool(cfg.supabase_url)
    anon_ok = bool(cfg.supabase_anon_key)
    service_ok = bool(cfg.supabase_service_role_key)
    jwt_ok = bool(cfg.supabase_jwt_secret)
    return SupabaseConfigStatus(
        configured=url_ok and service_ok,
        url_present=url_ok,
        anon_key_present=anon_ok,
        service_role_present=service_ok,
        jwt_secret_present=jwt_ok,
        storage_bucket=cfg.supabase_storage_bucket,
    )

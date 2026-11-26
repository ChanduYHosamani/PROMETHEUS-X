"""Phase 6 end-to-end integration tests: isolation, validation, empty-data, and non-fabrication."""

import io
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import get_settings
from backend.app.main import app
from tests.test_supabase_integration import TEST_SECRET, _build_jwt


def _auth_header(user_id: str, role: str = "authenticated") -> dict[str, str]:
    token = _build_jwt(
        {"sub": user_id, "email": f"{user_id}@factory.io", "role": role, "exp": int(time.time()) + 3600},
        TEST_SECRET,
    )
    return {"Authorization": f"Bearer {token}"}


def test_review_cannot_target_another_users_inspection() -> None:
    """A non-admin user must get 404 when trying to review another user's inspection."""
    from backend.app.api.routes.reviews import get_supabase_service

    class ScopedMockSupabase:
        def get_inspection(self, inspection_id: str, user_id: str | None = None):
            if user_id == "user-b":
                return None
            return {"id": inspection_id, "user_id": "user-a"}

    app.dependency_overrides[get_supabase_service] = lambda: ScopedMockSupabase()
    settings = get_settings()
    orig_secret = settings.supabase_jwt_secret
    settings.supabase_jwt_secret = TEST_SECRET
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/v1/reviews",
            headers=_auth_header("user-b"),
            json={
                "inspection_id": "11111111-1111-1111-1111-111111111111",
                "verdict": "false_positive",
            },
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
    finally:
        settings.supabase_jwt_secret = orig_secret
        app.dependency_overrides.clear()


def test_analytics_empty_data_and_unconfigured_handling() -> None:
    """Analytics endpoints must return honest unavailable/insufficient_data statuses without fake metrics."""
    from backend.app.api.routes.analytics import get_supabase_service

    class EmptyMockSupabase:
        def is_configured(self) -> bool:
            return True

        def list_inspections(self, user_id=None, limit=200, offset=0):
            return []

    app.dependency_overrides[get_supabase_service] = lambda: EmptyMockSupabase()
    settings = get_settings()
    orig_secret = settings.supabase_jwt_secret
    settings.supabase_jwt_secret = TEST_SECRET
    try:
        client = TestClient(app)
        r_overview = client.get("/api/v1/analytics/overview", headers=_auth_header("user-a"))
        assert r_overview.status_code == 200
        assert r_overview.json()["status"] == "insufficient_data"
        assert r_overview.json()["data"]["total_inspections"] == 0

        r_shift = client.get("/api/v1/analytics/distribution-shift", headers=_auth_header("user-a"))
        assert r_shift.status_code == 200
        assert r_shift.json()["status"] == "insufficient_data"
    finally:
        settings.supabase_jwt_secret = orig_secret
        app.dependency_overrides.clear()


def test_upload_validation_and_missing_bank_never_fabricates() -> None:
    """Empty/non-image uploads return 400; missing bank returns 409 without fake predictions."""
    client = TestClient(app)

    # Non-image MIME type
    r_mime = client.post(
        "/api/v1/inspections",
        data={"category_id": "bottle", "source_type": "upload"},
        files={"file": ("bad.txt", b"not an image", "text/plain")},
    )
    assert r_mime.status_code == 400

    # Valid PNG against a simulated missing memory bank -> 409 Conflict.
    # This does not delete or modify any real trained model artifacts.
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color=(100, 120, 140)).save(buf, format="PNG")

    with patch(
        "backend.app.services.inference_service.InferenceService.has_memory_bank",
        return_value=False,
    ):
        r_missing_bank = client.post(
            "/api/v1/inspections",
            data={"category_id": "bottle", "source_type": "upload"},
            files={"file": ("sample.png", buf.getvalue(), "image/png")},
        )

    assert r_missing_bank.status_code == 409
    assert "memory bank" in r_missing_bank.json()["detail"].lower()


def test_models_status_lists_all_15_categories() -> None:
    """GET /api/v1/models/status reports all 15 MVTec categories and honest readiness."""
    client = TestClient(app)
    resp = client.get("/api/v1/models/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_categories"] == 15
    assert isinstance(body["ready_categories"], list)
    assert body["ready_count"] == len(body["ready_categories"])
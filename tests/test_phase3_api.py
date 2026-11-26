"""Phase 3 automated tests for FastAPI routes, validation, auth, model management, and mocked Supabase."""

import base64
import hashlib
import hmac
from io import BytesIO
import json
import time
from unittest.mock import patch
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image

from backend.app.api.routes import analytics as analytics_route
from backend.app.api.routes import inspections as inspections_route
from backend.app.api.routes import reviews as reviews_route
from backend.app.core.config import get_settings
from backend.app.main import app
from backend.app.services.inference_service import (
    InferenceService,
    MemoryBankUnavailableError,
    get_inference_service,
)


def _make_hs256_jwt(sub: str, secret: str, exp_offset: int = 3600) -> str:
    def b64u(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    header = b64u(json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8"))
    payload = b64u(
        json.dumps({"sub": sub, "email": "inspector@prometheus-x.local", "role": "authenticated", "exp": time.time() + exp_offset}).encode("utf-8")
    )
    sig = hmac.new(secret.encode("utf-8"), f"{header}.{payload}".encode("ascii"), hashlib.sha256).digest()
    return f"{header}.{payload}.{b64u(sig)}"


def _png_bytes(width: int = 64, height: int = 64) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), color=(120, 140, 160)).save(buf, format="PNG")
    return buf.getvalue()


class MockSupabaseService:
    """In-memory mock of SupabaseService for isolated Phase 3 route testing."""

    def __init__(self, configured: bool = True) -> None:
        self._configured = configured
        self.inspections: Dict[str, Dict[str, Any]] = {}
        self.reviews: List[Dict[str, Any]] = []

    def is_configured(self) -> bool:
        return self._configured

    def upload_storage_object(self, object_path: str, data: bytes, content_type: str) -> str:
        return f"inspections/{object_path}"

    def create_inspection_record(
        self,
        inspection_payload: Dict[str, Any],
        result_payload: Dict[str, Any],
        detections_payload: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        insp_id = inspection_payload["id"]
        row = {
            **inspection_payload,
            "created_at": "2026-11-25T12:00:00Z",
            "inspection_results": [{**result_payload, "id": str(uuid4()), "defect_detections": detections_payload}],
        }
        self.inspections[insp_id] = row
        return {"inspection": row, "result": row["inspection_results"][0], "detections": detections_payload}

    def list_inspections(
        self, user_id: Optional[str] = None, category_id: Optional[str] = None, limit: int = 20, offset: int = 0
    ) -> List[Dict[str, Any]]:
        rows = list(self.inspections.values())
        if user_id:
            rows = [r for r in rows if r.get("user_id") == user_id]
        if category_id:
            rows = [r for r in rows if r.get("category_id") == category_id]
        return rows[offset : offset + limit]

    def get_inspection(self, inspection_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        row = self.inspections.get(inspection_id)
        if row and user_id and row.get("user_id") != user_id:
            return None
        return row

    def delete_inspection(self, inspection_id: str, user_id: Optional[str] = None) -> bool:
        row = self.get_inspection(inspection_id, user_id=user_id)
        if not row:
            return False
        del self.inspections[inspection_id]
        return True

    def create_review(self, review_payload: Dict[str, Any]) -> Dict[str, Any]:
        row = {
            **review_payload,
            "id": str(uuid4()),
            "created_at": "2026-11-25T12:05:00Z",
        }
        self.reviews.append(row)
        return row

    def list_reviews(
        self, inspection_id: Optional[str] = None, reviewer_id: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        rows = self.reviews
        if inspection_id:
            rows = [r for r in rows if r.get("inspection_id") == inspection_id]
        if reviewer_id:
            rows = [r for r in rows if r.get("reviewer_id") == reviewer_id]
        return rows[:limit]


class StubInferenceService(InferenceService):
    """Deterministic stub for testing POST /inspections without trained MVTec artifacts."""

    def __init__(self, bank_ready: bool = True) -> None:
        super().__init__()
        self._bank_ready = bank_ready

    def has_memory_bank(self, category_id: str) -> bool:
        return self._bank_ready

    async def predict(self, image_bytes: bytes, category_id: str) -> Dict[str, Any]:
        if not self._bank_ready:
            raise MemoryBankUnavailableError(
                f"Memory bank for category '{category_id}' is not available."
            )
        return {
            "category_id": category_id,
            "is_anomalous": True,
            "anomaly_score": 0.72,
            "calibrated_confidence": 0.81,
            "severity": "high",
            "image_size": {"width": 64, "height": 64},
            "heatmap_overlay_png": _png_bytes(64, 64),
            "detections": [
                {
                    "bbox_x": 0.2,
                    "bbox_y": 0.2,
                    "bbox_w": 0.3,
                    "bbox_h": 0.3,
                    "area_ratio": 0.09,
                    "peak_score": 0.88,
                }
            ],
            "inference_time_ms": 12.5,
        }


def test_models_status_and_missing_bank_409() -> None:
    client = TestClient(app)
    res = client.get("/api/v1/models/status")
    assert res.status_code == 200
    body = res.json()
    assert body["total_categories"] == 15
    assert "device" in body

    # Simulate a missing model without deleting real trained artifacts.
    with patch(
        "backend.app.services.inference_service.InferenceService.has_memory_bank",
        return_value=False,
    ):
        load_res = client.post("/api/v1/models/bottle/load")

    assert load_res.status_code == 409


def test_inspection_upload_validation_and_missing_bank() -> None:
    client = TestClient(app)
    # Invalid category
    r1 = client.post(
        "/api/v1/inspections",
        data={"category_id": "invalid_cat", "source_type": "upload"},
        files={"file": ("test.png", _png_bytes(), "image/png")},
    )
    assert r1.status_code == 400

    # Invalid content type
    r2 = client.post(
        "/api/v1/inspections",
        data={"category_id": "bottle", "source_type": "upload"},
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert r2.status_code == 400

    # Corrupt image bytes
    r3 = client.post(
        "/api/v1/inspections",
        data={"category_id": "bottle", "source_type": "upload"},
        files={"file": ("bad.png", b"not-a-real-png", "image/png")},
    )
    assert r3.status_code == 400

    # Valid image when memory bank is unavailable -> 409 Conflict
    app.dependency_overrides[get_inference_service] = lambda: StubInferenceService(bank_ready=False)
    try:
        r4 = client.post(
            "/api/v1/inspections",
            data={"category_id": "bottle", "source_type": "upload"},
            files={"file": ("good.png", _png_bytes(), "image/png")},
        )
        assert r4.status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_inspection_history_reviews_and_analytics_with_auth_and_mocks() -> None:
    settings = get_settings()
    orig_secret = settings.supabase_jwt_secret
    settings.supabase_jwt_secret = "test-phase3-jwt-secret"

    user_id = str(uuid4())
    token = _make_hs256_jwt(user_id, settings.supabase_jwt_secret)
    auth_headers = {"Authorization": f"Bearer {token}"}

    mock_sb = MockSupabaseService(configured=True)
    stub_inf = StubInferenceService(bank_ready=True)

    app.dependency_overrides[get_inference_service] = lambda: stub_inf
    app.dependency_overrides[inspections_route.get_supabase_service] = lambda: mock_sb
    app.dependency_overrides[reviews_route.get_supabase_service] = lambda: mock_sb
    app.dependency_overrides[analytics_route.get_supabase_service] = lambda: mock_sb

    client = TestClient(app)
    try:
        # Unauthenticated history request must be rejected
        assert client.get("/api/v1/inspections").status_code == 401

        # Analytics before any data -> insufficient_data
        ov_empty = client.get("/api/v1/analytics/overview", headers=auth_headers)
        assert ov_empty.status_code == 200
        assert ov_empty.json()["status"] == "insufficient_data"

        # Run inspection as authenticated user
        pred_res = client.post(
            "/api/v1/inspections",
            headers=auth_headers,
            data={"category_id": "bottle", "source_type": "upload"},
            files={"file": ("sample.png", _png_bytes(), "image/png")},
        )
        assert pred_res.status_code == 200
        pred_data = pred_res.json()
        assert pred_data["persisted_to_supabase"] is True
        assert pred_data["severity"] == "high"
        insp_id = pred_data["inspection_id"]

        # List & get inspection history
        hist_res = client.get("/api/v1/inspections", headers=auth_headers)
        assert hist_res.status_code == 200
        assert hist_res.json()["count"] == 1

        detail_res = client.get(f"/api/v1/inspections/{insp_id}", headers=auth_headers)
        assert detail_res.status_code == 200
        assert detail_res.json()["id"] == insp_id

        # Submit & list false-positive review
        rev_res = client.post(
            "/api/v1/reviews",
            headers=auth_headers,
            json={
                "inspection_id": insp_id,
                "verdict": "false_positive",
                "corrected_severity": "low",
                "notes": "Lighting reflection on glass bottle.",
            },
        )
        assert rev_res.status_code == 201
        assert rev_res.json()["verdict"] == "false_positive"

        rev_list = client.get("/api/v1/reviews", headers=auth_headers)
        assert rev_list.status_code == 200
        assert rev_list.json()["count"] == 1

        # Analytics overview now reflects 1 real stored inspection
        ov_res = client.get("/api/v1/analytics/overview", headers=auth_headers)
        assert ov_res.status_code == 200
        assert ov_res.json()["status"] == "ok"
        assert ov_res.json()["data"]["total_inspections"] == 1

        # Delete inspection
        del_res = client.delete(f"/api/v1/inspections/{insp_id}", headers=auth_headers)
        assert del_res.status_code == 200
        assert del_res.json()["deleted"] is True
    finally:
        app.dependency_overrides.clear()
        settings.supabase_jwt_secret = orig_secret

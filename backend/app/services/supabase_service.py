"""Supabase PostgreSQL (PostgREST) & Storage service using server-side credentials."""

from dataclasses import dataclass
import json
from typing import Any, Dict, List, Optional
from urllib import error, parse, request

from fastapi import HTTPException, status

from backend.app.core.config import Settings, get_settings
from backend.app.db.supabase_client import SupabaseConfigStatus, get_supabase_status


@dataclass
class SupabaseRequestResult:
    data: Any
    status_code: int


class SupabaseService:
    """Encapsulates persistence to Supabase PostgreSQL and Storage buckets."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def status(self) -> SupabaseConfigStatus:
        return get_supabase_status(self.settings)

    def is_configured(self) -> bool:
        return self.status().configured

    def require_configured(self) -> None:
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env.",
            )

    def _headers(self, prefer: Optional[str] = None, content_type: str = "application/json") -> Dict[str, str]:
        headers = {
            "apikey": self.settings.supabase_service_role_key,
            "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
            "Content-Type": content_type,
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        query: Optional[Dict[str, str]] = None,
    ) -> Any:
        self.require_configured()
        url = f"{self.settings.supabase_url}{path}"
        if query:
            url = f"{url}?{parse.urlencode(query)}"

        req = request.Request(url=url, data=body, method=method, headers=headers or self._headers())
        try:
            with request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Supabase request failed ({exc.code}): {detail or exc.reason}",
            ) from exc
        except error.URLError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unable to reach Supabase: {exc.reason}",
            ) from exc

    def upload_storage_object(self, object_path: str, data: bytes, content_type: str) -> str:
        """Upload a binary object (image or heatmap PNG) to Supabase Storage."""
        self.require_configured()
        bucket = self.settings.supabase_storage_bucket
        encoded_path = parse.quote(object_path.lstrip("/"))
        url = f"{self.settings.supabase_url}/storage/v1/object/{bucket}/{encoded_path}"
        headers = {
            "apikey": self.settings.supabase_service_role_key,
            "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
            "Content-Type": content_type,
            "x-upsert": "true",
        }
        req = request.Request(url=url, data=data, method="POST", headers=headers)
        try:
            with request.urlopen(req, timeout=20):
                return f"{bucket}/{object_path.lstrip('/')}"
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Supabase Storage upload failed ({exc.code}): {detail or exc.reason}",
            ) from exc

    def create_inspection_record(
        self,
        inspection_payload: Dict[str, Any],
        result_payload: Dict[str, Any],
        detections_payload: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Insert inspection, inspection_result, and defect_detections rows."""
        created_insp = self._request(
            "POST",
            "/rest/v1/inspections",
            body=json.dumps(inspection_payload).encode("utf-8"),
            headers=self._headers(prefer="return=representation"),
        )
        inspection_row = created_insp[0]

        result_payload = {**result_payload, "inspection_id": inspection_row["id"]}
        created_res = self._request(
            "POST",
            "/rest/v1/inspection_results",
            body=json.dumps(result_payload).encode("utf-8"),
            headers=self._headers(prefer="return=representation"),
        )
        result_row = created_res[0]

        detection_rows: List[Dict[str, Any]] = []
        if detections_payload:
            rows = [{**d, "inspection_result_id": result_row["id"]} for d in detections_payload]
            detection_rows = self._request(
                "POST",
                "/rest/v1/defect_detections",
                body=json.dumps(rows).encode("utf-8"),
                headers=self._headers(prefer="return=representation"),
            ) or []

        return {
            "inspection": inspection_row,
            "result": result_row,
            "detections": detection_rows,
        }

    def list_inspections(
        self,
        user_id: Optional[str] = None,
        category_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, str] = {
            "select": "*,inspection_results(*,defect_detections(*))",
            "order": "created_at.desc",
            "limit": str(limit),
            "offset": str(offset),
        }
        if user_id:
            query["user_id"] = f"eq.{user_id}"
        if category_id:
            query["category_id"] = f"eq.{category_id}"
        return self._request("GET", "/rest/v1/inspections", query=query) or []

    def get_inspection(self, inspection_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        query: Dict[str, str] = {
            "id": f"eq.{inspection_id}",
            "select": "*,inspection_results(*,defect_detections(*)),review_records(*)",
        }
        if user_id:
            query["user_id"] = f"eq.{user_id}"
        rows = self._request("GET", "/rest/v1/inspections", query=query) or []
        return rows[0] if rows else None

    def delete_inspection(self, inspection_id: str, user_id: Optional[str] = None) -> bool:
        query: Dict[str, str] = {"id": f"eq.{inspection_id}"}
        if user_id:
            query["user_id"] = f"eq.{user_id}"
        deleted = self._request(
            "DELETE",
            "/rest/v1/inspections",
            headers=self._headers(prefer="return=representation"),
            query=query,
        )
        return bool(deleted)

    def create_review(self, review_payload: Dict[str, Any]) -> Dict[str, Any]:
        rows = self._request(
            "POST",
            "/rest/v1/review_records",
            body=json.dumps(review_payload).encode("utf-8"),
            headers=self._headers(prefer="return=representation"),
        )
        return rows[0]

    def list_reviews(
        self,
        inspection_id: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, str] = {
            "select": "*",
            "order": "created_at.desc",
            "limit": str(limit),
        }
        if inspection_id:
            query["inspection_id"] = f"eq.{inspection_id}"
        if reviewer_id:
            query["reviewer_id"] = f"eq.{reviewer_id}"
        return self._request("GET", "/rest/v1/review_records", query=query) or []

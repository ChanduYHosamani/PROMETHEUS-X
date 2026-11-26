"""Analytics & distribution-shift endpoints backed by real stored inspection data."""

from collections import Counter
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from backend.app.core.security import AuthenticatedUser, get_current_user
from backend.app.schemas.inspection import AnalyticsStatusOut
from backend.app.services.supabase_service import SupabaseService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_supabase_service() -> SupabaseService:
    return SupabaseService()


@router.get("/overview", response_model=AnalyticsStatusOut)
async def get_analytics_overview(
    current_user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
) -> AnalyticsStatusOut:
    """Compute inspection summary metrics from real stored Supabase records."""
    if not supabase.is_configured():
        return AnalyticsStatusOut(
            status="unavailable",
            message="Supabase is not configured; analytics require persisted inspection records.",
            data={},
        )

    owner_filter = None if current_user.role == "admin" else current_user.id
    rows = supabase.list_inspections(user_id=owner_filter, limit=200, offset=0)
    if not rows:
        return AnalyticsStatusOut(
            status="insufficient_data",
            message="No stored inspections available yet.",
            data={"total_inspections": 0},
        )

    severity_counts: Counter = Counter()
    category_counts: Counter = Counter()
    anomalous_count = 0

    for row in rows:
        category_counts[row["category_id"]] += 1
        results = row.get("inspection_results") or []
        res = results[0] if isinstance(results, list) and results else (results if isinstance(results, dict) else None)
        if res:
            if res.get("is_anomalous"):
                anomalous_count += 1
            if res.get("severity"):
                severity_counts[res["severity"]] += 1

    total = len(rows)
    return AnalyticsStatusOut(
        status="ok",
        data={
            "total_inspections": total,
            "anomalous_count": anomalous_count,
            "normal_count": total - anomalous_count,
            "anomaly_rate": round(anomalous_count / total, 4),
            "by_severity": dict(severity_counts),
            "by_category": dict(category_counts),
        },
    )


@router.get("/distribution-shift", response_model=AnalyticsStatusOut)
async def get_distribution_shift(
    current_user: AuthenticatedUser = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
) -> AnalyticsStatusOut:
    """Compute per-category score drift from real stored inspection results."""
    if not supabase.is_configured():
        return AnalyticsStatusOut(
            status="unavailable",
            message="Supabase is not configured; distribution-shift monitoring requires stored results.",
            data={},
        )

    owner_filter = None if current_user.role == "admin" else current_user.id
    rows = supabase.list_inspections(user_id=owner_filter, limit=200, offset=0)
    scores_by_cat: Dict[str, List[float]] = {}

    for row in rows:
        results = row.get("inspection_results") or []
        res = results[0] if isinstance(results, list) and results else (results if isinstance(results, dict) else None)
        if res and res.get("anomaly_score") is not None:
            scores_by_cat.setdefault(row["category_id"], []).append(float(res["anomaly_score"]))

    if not scores_by_cat or sum(len(v) for v in scores_by_cat.values()) < 5:
        return AnalyticsStatusOut(
            status="insufficient_data",
            message="At least 5 completed inspections are required to compute distribution-shift statistics.",
            data={"sample_count": sum(len(v) for v in scores_by_cat.values())},
        )

    per_category = {
        cat: {
            "count": len(vals),
            "mean_anomaly_score": round(sum(vals) / len(vals), 4),
            "max_anomaly_score": round(max(vals), 4),
        }
        for cat, vals in scores_by_cat.items()
    }
    return AnalyticsStatusOut(status="ok", data={"categories": per_category})

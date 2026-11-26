"""Inspection request and response schemas."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class DefectRegionOut(BaseModel):
    bbox_x: float
    bbox_y: float
    bbox_w: float
    bbox_h: float
    area_ratio: float
    peak_score: float
    label: Optional[str] = None


class InspectionPredictOut(BaseModel):
    inspection_id: str
    category_id: str
    source_type: Literal["upload", "camera"]
    status: Literal["completed"]
    is_anomalous: bool
    anomaly_score: float
    calibrated_confidence: float
    severity: Literal["low", "medium", "high", "critical"]
    image_size: Dict[str, int]
    heatmap_base64: str
    heatmap_storage_path: Optional[str] = None
    image_storage_path: Optional[str] = None
    detections: List[DefectRegionOut] = Field(default_factory=list)
    inference_time_ms: float
    persisted_to_supabase: bool


class InspectionHistoryListOut(BaseModel):
    items: List[Dict[str, Any]]
    count: int
    limit: int
    offset: int


class InspectionDeleteOut(BaseModel):
    deleted: bool
    inspection_id: str


class AnalyticsStatusOut(BaseModel):
    status: Literal["ok", "insufficient_data", "unavailable"]
    message: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)

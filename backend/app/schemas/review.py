"""False-positive & human-in-the-loop review schemas."""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewCreateIn(BaseModel):
    inspection_id: UUID
    verdict: Literal["confirmed_defect", "false_positive", "uncertain"]
    corrected_severity: Optional[Literal["low", "medium", "high", "critical"]] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class ReviewOut(BaseModel):
    id: str
    inspection_id: str
    reviewer_id: str
    verdict: Literal["confirmed_defect", "false_positive", "uncertain"]
    corrected_severity: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


class ReviewListOut(BaseModel):
    items: List[ReviewOut]
    count: int

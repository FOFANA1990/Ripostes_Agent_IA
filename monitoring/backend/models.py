"""Schemas API (Pydantic) pour le monitoring CNC."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

DecisionAction = Literal["validate", "edit", "reject", "factcheck"]
EventStatus = Literal["pending", "approved", "edited_approved", "rejected", "needs_factcheck"]


class DecisionRequest(BaseModel):
    action: DecisionAction
    edited_text: Optional[str] = None      # requis pour 'edit'
    reason: Optional[str] = None           # requis pour 'reject'
    operator: str = "CNC"

    @model_validator(mode="after")
    def _check(self) -> "DecisionRequest":
        if self.action == "edit" and not (self.edited_text or "").strip():
            raise ValueError("edited_text requis pour l'action 'edit'.")
        if self.action == "reject" and not (self.reason or "").strip():
            raise ValueError("reason requis pour l'action 'reject'.")
        return self


class AuditEntry(BaseModel):
    event_id: str
    action: DecisionAction
    operator: str
    reason: Optional[str] = None
    at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Kpis(BaseModel):
    events_detected: int
    pending_validation: int
    reach_cumule: int
    peak_volume: int
    total_posts: int
    negative_share_pct: float


class Dashboard(BaseModel):
    kpis: Kpis
    timeline: list[dict[str, Any]]
    alerts: list[dict[str, Any]]

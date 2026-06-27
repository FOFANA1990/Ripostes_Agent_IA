"""
store.py — Etat en memoire du monitoring (seed + decisions + audit).

Source de verite cote serveur. Charge monitoring_seed.json, expose les
evenements, applique les decisions de l'operateur et tient une piste d'audit.
NB : etat en memoire (non persistant entre redemarrages) — suffisant pour la demo.
"""
from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from models import AuditEntry, DecisionRequest

SEED_PATH = Path(__file__).resolve().parent / "monitoring_seed.json"

_STATUS_BY_ACTION = {
    "validate": "approved",
    "edit": "edited_approved",
    "reject": "rejected",
    "factcheck": "needs_factcheck",
}


class Store:
    def __init__(self, seed_path: Path = SEED_PATH):
        self._lock = Lock()
        raw = json.loads(seed_path.read_text(encoding="utf-8"))
        self.kpis: dict[str, Any] = raw["kpis"]
        self.timeline: list[dict] = raw["timeline"]
        self.alerts: list[dict] = raw["alerts"]
        self._events: dict[str, dict] = {}
        for i, ev in enumerate(raw["events"]):
            eid = ev["event"]["event_id"]
            if eid in self._events:           # garantit l'unicite des identifiants
                eid = f"{eid}-{i}"
            ev["id"] = eid
            self._events[eid] = ev
        self.audit: list[dict] = []

    # ------------------------------- lectures ------------------------------ #
    def dashboard(self) -> dict:
        return {"kpis": self._live_kpis(), "timeline": self.timeline, "alerts": self.alerts}

    def list_events(self) -> list[dict]:
        return [self._summary(e) for e in self._events.values()]

    def get_event(self, event_id: str) -> dict | None:
        return self._events.get(event_id)

    def get_audit(self) -> list[dict]:
        return self.audit

    # ------------------------------- ecriture ------------------------------ #
    def apply_decision(self, event_id: str, req: DecisionRequest) -> dict | None:
        with self._lock:
            ev = self._events.get(event_id)
            if ev is None:
                return None
            ev["status"] = _STATUS_BY_ACTION[req.action]
            if req.action == "edit":
                ev["riposte"]["brouillon"] = req.edited_text
                ev["edited"] = True
            ev["decision"] = {"action": req.action, "reason": req.reason, "operator": req.operator}
            self.audit.insert(0, AuditEntry(event_id=event_id, action=req.action,
                                            operator=req.operator, reason=req.reason).model_dump())
            return ev

    # ------------------------------- internes ------------------------------ #
    def _live_kpis(self) -> dict:
        k = dict(self.kpis)
        k["pending_validation"] = sum(1 for e in self._events.values() if e["status"] == "pending")
        return k

    @staticmethod
    def _summary(ev: dict) -> dict:
        e = ev["event"]
        return {
            "id": ev["id"],
            "event_id": e["event_id"],
            "level": e["level"],
            "status": ev["status"],
            "peak_hour": e["peak_hour"],
            "peak_volume": e["peak_volume"],
            "velocity_factor": e["velocity_factor"],
            "detected_at": ev["detected_at"],
            "narratif_dominant": ev["report"]["narratif_dominant"],
            "top_amplifiers": [a["handle"] for a in e["top_amplifiers"][:3]],
        }

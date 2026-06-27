"""
main.py — API FastAPI du monitoring CNC.

Expose le tableau de bord (KPIs, timeline, alertes), la file d'evenements a
valider, le detail d'un evenement et l'endpoint de decision de l'operateur.

Lancer :
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import Dashboard, DecisionRequest
from store import Store

app = FastAPI(title="CNC — Monitoring & Validation", version="1.0.0")

# CORS pour le serveur de dev Vite.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store = Store()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/dashboard", response_model=Dashboard)
def get_dashboard() -> dict:
    return store.dashboard()


@app.get("/api/events")
def list_events() -> list[dict]:
    return store.list_events()


@app.get("/api/events/{event_id}")
def get_event(event_id: str) -> dict:
    ev = store.get_event(event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="Evenement introuvable")
    return ev


@app.post("/api/events/{event_id}/decision")
def decide(event_id: str, req: DecisionRequest) -> dict:
    ev = store.apply_decision(event_id, req)
    if ev is None:
        raise HTTPException(status_code=404, detail="Evenement introuvable")
    return ev


@app.get("/api/audit")
def get_audit() -> list[dict]:
    return store.get_audit()

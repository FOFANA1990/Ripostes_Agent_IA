"""
orchestrator.py — Chaîne séquentielle des 3 agents (mode batch).

    Détection (déterministe)  ->  Analyse (LLM)  ->  Riposte (LLM)

La supervision humaine intervient APRÈS (rien n'est publié).
"""
from __future__ import annotations

import logging

import pandas as pd
from pydantic import BaseModel

from agents import AnalysisAgent, DetectionAgent, RiposteAgent
from config import AppConfig, get_chat_model
from schemas import DetectedEvent, RiposteDraft, SituationReport

logger = logging.getLogger("agents_cnc.orchestrator")


class EventBundle(BaseModel):
    """Résultat complet pour un événement : détection + analyse + riposte."""
    event: DetectedEvent
    report: SituationReport
    riposte: RiposteDraft


class PipelineResult(BaseModel):
    provider: str
    n_events_detected: int
    bundles: list[EventBundle]


class Orchestrator:
    def __init__(self, app: AppConfig):
        self.app = app
        model = get_chat_model(app)                 # None en mode mock
        self.detection = DetectionAgent(app.detection)
        self.analysis = AnalysisAgent(model)
        self.riposte = RiposteAgent(model)

    def run(self, df: pd.DataFrame, max_events: int = 3) -> PipelineResult:
        events = self.detection.run(df)
        selected = events[:max_events]
        logger.info("%d événement(s) détecté(s), %d traité(s) par les agents LLM.",
                    len(events), len(selected))

        bundles: list[EventBundle] = []
        for ev in selected:
            report = self.analysis.analyze(ev)
            riposte = self.riposte.draft(report)
            bundles.append(EventBundle(event=ev, report=report, riposte=riposte))

        return PipelineResult(provider=self.app.llm.provider,
                              n_events_detected=len(events), bundles=bundles)

"""
analysis_agent.py — Agent 2 : Analyse (LLM via LangChain).

Transforme un événement détecté (faits chiffrés) en une fiche de situation
rédigée. Garde-fous anti-hallucination :
  - le LLM ne voit QUE les faits fournis (ancrage strict) ;
  - sortie contrainte par un schéma Pydantic (with_structured_output) ;
  - consigne explicite : « non déterminable » si l'info manque, ne rien inventer ;
  - il NE tranche PAS la véracité (réservé au futur agent de fact-check).

Mode mock (model=None) : repli déterministe qui construit la fiche à partir des faits.
"""
from __future__ import annotations

import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from schemas import DetectedEvent, SituationReport

logger = logging.getLogger("agents_cnc.analysis")

_SYSTEM = (
    "Tu es un analyste de veille pour le CNC. Tu produis une fiche de situation "
    "FACTUELLE à partir UNIQUEMENT des faits fournis (JSON). "
    "Règles strictes : n'invente aucun chiffre, aucun compte, aucune affirmation. "
    "Si une information n'est pas dans les faits, écris 'non déterminable'. "
    "Tu ne juges PAS si les affirmations sont vraies ou fausses : tu les listes "
    "comme 'à vérifier'. Réponds en français."
)

_HUMAN = (
    "Faits de l'événement détecté :\n```json\n{facts}\n```\n\n"
    "Rédige la fiche de situation structurée correspondante."
)


class AnalysisAgent:
    def __init__(self, model):
        self.model = model
        self._chain = None
        if model is not None:
            prompt = ChatPromptTemplate.from_messages([("system", _SYSTEM), ("human", _HUMAN)])
            self._chain = prompt | model.with_structured_output(SituationReport)

    def analyze(self, event: DetectedEvent) -> SituationReport:
        facts = self._facts(event)
        if self._chain is None:
            return self._mock(event, facts)
        logger.info("Analyse LLM de %s", event.event_id)
        report = self._chain.invoke({"facts": json.dumps(facts, ensure_ascii=False, indent=2)})
        report.event_id = event.event_id  # on garantit la cohérence de l'identifiant
        return report

    # -------------------------- Ancrage / faits ---------------------------- #
    @staticmethod
    def _facts(event: DetectedEvent) -> dict:
        """Sélectionne les faits transmis au LLM (rien d'autre)."""
        return {
            "event_id": event.event_id,
            "periode": [event.window_start, event.window_end],
            "pic": {"heure": event.peak_hour, "volume_horaire": event.peak_volume,
                    "facteur_vitesse": event.velocity_factor},
            "volume_total": event.total_volume,
            "sentiment": event.sentiment_counts,
            "narratifs_mots_cles": event.narrative_hits,
            "amplificateurs": [a.model_dump() for a in event.top_amplifiers],
            "posts_sources": [s.model_dump() for s in event.source_posts],
        }

    # ----------------------------- Repli mock ------------------------------ #
    @staticmethod
    def _mock(event: DetectedEvent, facts: dict) -> SituationReport:
        narr = max(event.narrative_hits, key=event.narrative_hits.get) if event.narrative_hits else "non déterminable"
        total = sum(event.sentiment_counts.values()) or 1
        neg = event.sentiment_counts.get("negative", 0)
        return SituationReport(
            event_id=event.event_id,
            resume=(f"[MOCK] Emballement détecté au pic du {event.peak_hour} "
                    f"({event.peak_volume} posts/h, {event.total_volume} posts sur la fenêtre)."),
            narratif_dominant=narr.replace("_", " "),
            justification_narratif=f"[MOCK] Angle le plus fréquent dans les mots-clés : {event.narrative_hits}.",
            acteurs_cles=[a.handle for a in event.top_amplifiers[:5]],
            tonalite=f"{round(neg/total*100)}% de posts négatifs sur la fenêtre.",
            affirmations_a_verifier=[s.text for s in event.source_posts[:3] if s.text],
            niveau_confiance="moyen",
            post_ids_source=[s.post_id for s in event.source_posts if s.post_id],
        )

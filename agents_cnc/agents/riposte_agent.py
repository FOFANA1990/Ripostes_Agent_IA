"""
riposte_agent.py — Agent 3 : Riposte (LLM via LangChain).

Produit un BROUILLON de réponse à partir de la fiche de situation. Jamais publié :
`validation_humaine_requise = True` est imposé par le schéma.

Garde-fous : s'appuie uniquement sur la fiche fournie ; ton factuel et mesuré ;
n'invente pas de chiffres ; signale ce qui doit être vérifié avant diffusion.

Mode mock (model=None) : repli déterministe (gabarit de brouillon).
"""
from __future__ import annotations

import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from schemas import RiposteDraft, SituationReport

logger = logging.getLogger("agents_cnc.riposte")

_SYSTEM = (
    "Tu es chargé de communication au CNC. À partir de la fiche de situation fournie, "
    "tu proposes UN brouillon de riposte mesuré, factuel et non polémique. "
    "Règles : ne cite aucun chiffre absent de la fiche ; appuie-toi sur les faits ; "
    "reste sobre et institutionnel ; n'attaque pas les personnes. "
    "Ce texte est un BROUILLON soumis à validation humaine. Réponds en français."
)
_HUMAN = (
    "Fiche de situation :\n```json\n{report}\n```\n\n"
    "Propose le brouillon de riposte structuré."
)


class RiposteAgent:
    def __init__(self, model):
        self.model = model
        self._chain = None
        if model is not None:
            prompt = ChatPromptTemplate.from_messages([("system", _SYSTEM), ("human", _HUMAN)])
            self._chain = prompt | model.with_structured_output(RiposteDraft)

    def draft(self, report: SituationReport) -> RiposteDraft:
        if self._chain is None:
            return self._mock(report)
        logger.info("Rédaction LLM de la riposte pour %s", report.event_id)
        out = self._chain.invoke({"report": report.model_dump_json(indent=2)})
        out.validation_humaine_requise = True  # invariant de sécurité
        return out

    @staticmethod
    def _mock(report: SituationReport) -> RiposteDraft:
        return RiposteDraft(
            angle=f"Répondre sur l'angle « {report.narratif_dominant} » avec des faits sourcés.",
            canal="Communiqué court + post X épinglé",
            tonalite="Factuelle, institutionnelle, non polémique",
            brouillon=("[MOCK] Le CNC apporte des précisions factuelles concernant "
                       f"« {report.narratif_dominant} ». [À compléter avec les chiffres vérifiés.]"),
            appui_factuel=["Fiche de situation " + report.event_id, "Données à confirmer par fact-check"],
            mises_en_garde=["Brouillon non vérifié — fact-check requis avant toute diffusion."],
        )

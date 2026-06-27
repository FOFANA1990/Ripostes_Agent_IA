"""
schemas.py — Contrats de données (Pydantic) échangés entre les agents.

Toutes les sorties d'agents sont **typées et validées**. Cela contraint le LLM
à produire une structure exacte (réduction des hallucinations) et garantit des
interfaces stables entre les agents.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

AlertLevel = Literal["faible", "montee", "crise"]


# --------------------------------------------------------------------------- #
# Agent 1 — Détection (déterministe)
# --------------------------------------------------------------------------- #

class Amplifier(BaseModel):
    """Un compte qui relaie massivement (calculé, non inféré)."""
    handle: str
    reprises: int


class SourcePost(BaseModel):
    """Post source d'une cascade, utilisé pour l'ancrage et la citation."""
    post_id: str
    url: str
    author: str
    retweets: int
    text: str


class DetectedEvent(BaseModel):
    """
    Événement viral détecté par l'agent de veille.
    Tous les champs sont des FAITS calculés à partir du corpus.
    """
    event_id: str
    level: AlertLevel
    window_start: str
    window_end: str
    peak_hour: str
    peak_volume: int
    total_volume: int
    velocity_factor: float = Field(..., description="Volume du pic / ligne de base")
    trigger_reason: str
    top_amplifiers: list[Amplifier]
    source_posts: list[SourcePost]
    sentiment_counts: dict[str, int]
    narrative_hits: dict[str, int]


# --------------------------------------------------------------------------- #
# Agent 2 — Analyse (LLM)
# --------------------------------------------------------------------------- #

class SituationReport(BaseModel):
    """Fiche de situation rédigée par l'agent d'analyse, ancrée sur les faits."""
    event_id: str
    resume: str = Field(..., description="Synthèse factuelle de l'événement, 2-3 phrases")
    narratif_dominant: str = Field(..., description="L'angle qui fédère, en langage naturel")
    justification_narratif: str = Field(..., description="Pourquoi, en s'appuyant sur les faits fournis")
    acteurs_cles: list[str] = Field(..., description="Comptes moteurs, repris des faits fournis")
    tonalite: str = Field(..., description="Lecture du sentiment (à partir des compteurs fournis)")
    affirmations_a_verifier: list[str] = Field(
        default_factory=list,
        description="Affirmations factuelles circulant, À VÉRIFIER (ne pas trancher ici)",
    )
    niveau_confiance: Literal["faible", "moyen", "eleve"]
    post_ids_source: list[str] = Field(..., description="postID cités comme appui")


# --------------------------------------------------------------------------- #
# Agent 3 — Riposte (LLM)
# --------------------------------------------------------------------------- #

class RiposteDraft(BaseModel):
    """Brouillon de riposte. JAMAIS publié automatiquement."""
    angle: str = Field(..., description="L'angle de réponse recommandé")
    canal: str = Field(..., description="Canal suggéré (ex. communiqué, post X, FAQ)")
    tonalite: str
    brouillon: str = Field(..., description="Texte de réponse proposé")
    appui_factuel: list[str] = Field(..., description="Faits vérifiés sur lesquels s'appuie la réponse")
    mises_en_garde: list[str] = Field(default_factory=list)
    validation_humaine_requise: Literal[True] = True

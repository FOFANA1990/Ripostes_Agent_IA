"""
config.py — Configuration de l'application (YAML valide par Pydantic).

Architecture de config professionnelle pour applications d'agents :
  - GENERIQUE : LLMConfig, RuntimeConfig, TriggerConfig  (reutilisables tels quels)
  - DOMAINE   : DetectionConfig                          (a adapter par probleme)

La config NON secrete est lue depuis `config.yaml` ; les SECRETS (cles API)
restent en variables d'environnement. `AppConfig` agrege le tout et le valide.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from data_loader import DEFAULT_NARRATIVES

AlertLevel = Literal["faible", "montee", "crise"]
Provider = Literal["gemini", "mistral", "mock"]

# Modele par defaut si `llm.model` n'est pas precise.
DEFAULT_MODELS = {"gemini": "gemini-1.5-flash", "mistral": "mistral-small-latest"}


# --------------------------------------------------------------------------- #
# Couche GENERIQUE (reutilisable pour tout projet d'agents)
# --------------------------------------------------------------------------- #
class LLMConfig(BaseModel):
    provider: Provider = "mock"
    model: str | None = None
    temperature: float = 0.0
    max_retries: int = 2
    timeout: int = 60


class RuntimeConfig(BaseModel):
    log_level: str = "INFO"
    output_dir: str = "resultats"
    verbose: bool = True


class TriggerConfig(BaseModel):
    """Politique de declenchement des agents en aval (generique)."""
    mode: Literal["on_threshold", "on_escalation"] = "on_threshold"
    min_level: AlertLevel = "montee"
    once_per_event: bool = True
    cooldown_min: int = 0


# --------------------------------------------------------------------------- #
# Couche DOMAINE (specifique CNC — a remplacer pour un autre probleme)
# --------------------------------------------------------------------------- #
class DetectionConfig(BaseModel):
    baseline_window_h: int = 24
    factor_faible: float = 3.0
    factor_montee: float = 6.0
    factor_crise: float = 12.0
    min_baseline: float = 5.0
    close_after_h: int = 6
    max_source_posts: int = 5
    max_amplifiers: int = 8
    narratives: dict[str, list[str]] = Field(default_factory=dict)

    def resolved_narratives(self) -> dict[str, list[str]]:
        """Narratifs du YAML, ou valeurs par defaut du domaine si vide."""
        return self.narratives or DEFAULT_NARRATIVES


# --------------------------------------------------------------------------- #
# Agregat racine
# --------------------------------------------------------------------------- #
class AppConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    trigger: TriggerConfig = Field(default_factory=TriggerConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)


def load_config(path: str | Path = "config.yaml", *, provider_override: str | None = None) -> "AppConfig":
    """Charge et valide la config depuis un YAML. `provider_override` prime (ex. CLI)."""
    path = Path(path)
    data: dict = {}
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    app = AppConfig.model_validate(data)
    if provider_override:
        new_llm = app.llm.model_copy(update={"provider": provider_override})
        app = app.model_copy(update={"llm": new_llm})
    _setup_logging(app.runtime.log_level)
    return app


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


logger = logging.getLogger("agents_cnc")


def get_chat_model(app: "AppConfig"):
    """Fabrique de modele LLM (generique). Renvoie None en mode `mock`."""
    llm = app.llm
    if llm.provider == "mock":
        logger.warning("Mode MOCK : aucun appel LLM reel (agents 2 & 3 en repli deterministe).")
        return None

    model_name = llm.model or DEFAULT_MODELS[llm.provider]
    if llm.provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        if not os.getenv("GOOGLE_API_KEY"):
            raise EnvironmentError("GOOGLE_API_KEY manquante pour le fournisseur 'gemini'.")
        return ChatGoogleGenerativeAI(model=model_name, temperature=llm.temperature,
                                      max_retries=llm.max_retries, timeout=llm.timeout)
    if llm.provider == "mistral":
        from langchain_mistralai import ChatMistralAI
        if not os.getenv("MISTRAL_API_KEY"):
            raise EnvironmentError("MISTRAL_API_KEY manquante pour le fournisseur 'mistral'.")
        return ChatMistralAI(model=model_name, temperature=llm.temperature,
                             max_retries=llm.max_retries, timeout=llm.timeout)
    raise ValueError(f"Fournisseur inconnu : {llm.provider}")

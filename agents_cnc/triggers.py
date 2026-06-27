"""
triggers.py — Politique de déclenchement (GÉNÉRIQUE, réutilisable).

Découple « quand déclencher » de « comment détecter ». Le domaine produit un
SIGNAL (un niveau de sévérité par instant) ; la TriggerPolicy décide si le
processus aval doit se lancer, selon une config (mode, seuil, anti-rebond,
cooldown). Réutilisable pour n'importe quel agent piloté par signal.
"""
from __future__ import annotations

from typing import Protocol

import pandas as pd

from agents.detection_agent import _LEVEL_ORDER
from config import TriggerConfig


class _HasTriggerState(Protocol):
    """Contrat minimal attendu de l'objet d'état d'événement."""
    last_trigger_ts: pd.Timestamp | None
    last_trigger_level: str | None


class TriggerPolicy:
    def __init__(self, cfg: TriggerConfig):
        self.cfg = cfg

    def should_fire(self, state: _HasTriggerState, level: str | None, now: pd.Timestamp) -> bool:
        """Décide si le pipeline aval doit se déclencher à cet instant."""
        if level is None:
            return False
        if _LEVEL_ORDER[level] < _LEVEL_ORDER[self.cfg.min_level]:
            return False

        # Anti-rebond temporel.
        if state.last_trigger_ts is not None and self.cfg.cooldown_min > 0:
            elapsed_min = (now - state.last_trigger_ts).total_seconds() / 60.0
            if elapsed_min < self.cfg.cooldown_min:
                return False

        if self.cfg.mode == "on_threshold":
            # Un seul déclenchement par événement si once_per_event.
            if self.cfg.once_per_event and state.last_trigger_ts is not None:
                return False
            return True

        # mode == "on_escalation" : re-déclenche à chaque montée vers un palier supérieur.
        if state.last_trigger_level is None:
            return True
        return _LEVEL_ORDER[level] > _LEVEL_ORDER[state.last_trigger_level]

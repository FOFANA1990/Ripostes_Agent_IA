"""
streaming.py — Simulation TEMPS REEL par rejeu du dataset.

On fait defiler le corpus dans l'ordre chronologique, heure simulee par heure
simulee. La detection est incrementale : a chaque instant, elle ne connait que
le PASSE. La decision de declencher les agents aval est deleguee a une
`TriggerPolicy` configurable (cf. triggers.py + section `trigger` de config.yaml).

NB : simulation fondee sur des donnees historiques. Le temps reel est reconstitue
en rejouant les horodatages, pas en interrogeant X en direct.
"""
from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field

import pandas as pd

from agents import AnalysisAgent, RiposteAgent
from agents.detection_agent import assemble_event, classify_level, _LEVEL_ORDER
from config import AppConfig, get_chat_model
from orchestrator import EventBundle, PipelineResult
from schemas import DetectedEvent
from triggers import TriggerPolicy

logger = logging.getLogger("agents_cnc.streaming")

_ICON = {"faible": "[F]", "montee": "[M]", "crise": "[C]"}


@dataclass
class _EventState:
    """Etat d'un evenement en cours de construction pendant le rejeu."""
    start_ts: pd.Timestamp
    rows: list = field(default_factory=list)
    peak_ts: pd.Timestamp | None = None
    peak_vol: int = 0
    peak_ratio: float = 0.0
    highest: str = "faible"
    calm_streak: int = 0
    last_trigger_ts: pd.Timestamp | None = None
    last_trigger_level: str | None = None


class StreamingDetector:
    """Detection incrementale alimentee heure par heure."""

    def __init__(self, cfg, policy: TriggerPolicy):
        self.cfg = cfg
        self.policy = policy
        self._baseline = deque(maxlen=cfg.baseline_window_h)
        self._event: _EventState | None = None

    def feed_hour(self, ts: pd.Timestamp, hour_df: pd.DataFrame) -> dict:
        """Traite une heure simulee. Renvoie volume, niveau, alertes et eventuel declenchement."""
        vol = len(hour_df)
        baseline = max(pd.Series(self._baseline).median() if self._baseline else 0.0,
                       self.cfg.min_baseline)
        ratio = vol / baseline
        level = classify_level(ratio, self.cfg)
        out = {"ts": ts, "volume": vol, "ratio": ratio, "level": level,
               "alerts": [], "trigger": None}

        if level is not None:
            if self._event is None:
                self._event = _EventState(start_ts=ts, highest=level)
                out["alerts"].append(f"{_ICON[level]} OUVERTURE d'alerte [{level}] a {ts:%d/%m %H:%M}")
            ev = self._event
            ev.rows.append(hour_df)
            ev.calm_streak = 0
            if vol > ev.peak_vol:
                ev.peak_vol, ev.peak_ts, ev.peak_ratio = vol, ts, ratio
            if _LEVEL_ORDER[level] > _LEVEL_ORDER[ev.highest]:
                ev.highest = level
                out["alerts"].append(f"{_ICON[level]} ESCALADE -> [{level}] a {ts:%d/%m %H:%M}")
            if self.policy.should_fire(ev, ev.highest, ts):
                out["trigger"] = self._snapshot(ts)
                ev.last_trigger_ts = ts
                ev.last_trigger_level = ev.highest
        elif self._event is not None:
            self._event.calm_streak += 1
            if self._event.calm_streak >= self.cfg.close_after_h:
                out["alerts"].append(f"[ok] Cloture de l'evenement (retour au calme) a {ts:%d/%m %H:%M}")
                self._event = None

        self._baseline.append(vol)
        return out

    def _snapshot(self, now_ts: pd.Timestamp) -> DetectedEvent:
        """Assemble l'evenement a partir des SEULS posts connus jusqu'a maintenant."""
        ev = self._event
        window = pd.concat(ev.rows, ignore_index=True)
        return assemble_event(
            window, window, self.cfg, level=ev.highest,
            peak_ts=ev.peak_ts, peak_vol=ev.peak_vol, peak_ratio=ev.peak_ratio,
            window_start=ev.start_ts, window_end=now_ts + pd.Timedelta(hours=1),
        )


class StreamSession:
    """Pilote le rejeu : horloge simulee + agents declenches en direct."""

    def __init__(self, app: AppConfig):
        self.app = app
        model = get_chat_model(app)
        self.detector = StreamingDetector(app.detection, TriggerPolicy(app.trigger))
        self.analysis = AnalysisAgent(model)
        self.riposte = RiposteAgent(model)

    def run(self, df: pd.DataFrame, hour_delay: float = 0.0,
            max_triggers: int = 3, verbose: bool | None = None) -> PipelineResult:
        verbose = self.app.runtime.verbose if verbose is None else verbose
        df = df.copy()
        df["__hour"] = df["Date"].dt.floor("h")
        groups = dict(tuple(df.groupby("__hour")))
        clock = pd.date_range(df["__hour"].min(), df["__hour"].max(), freq="h")

        empty = df.iloc[0:0]
        bundles: list = []
        n_triggers = 0
        current_day = None

        if verbose:
            print(f"\n[REJEU TEMPS REEL] {clock[0]:%d/%m %H:%M} -> {clock[-1]:%d/%m %H:%M} "
                  f"({len(clock)} heures simulees) | trigger={self.app.trigger.mode}\n" + "-" * 64)

        for ts in clock:
            hour_df = groups.get(ts, empty)
            res = self.detector.feed_hour(ts, hour_df)

            if verbose and ts.date() != current_day:
                current_day = ts.date()
                print(f"--- jour {ts:%d/%m} ---")
            if verbose and res["level"] is not None:
                print(f"   {ts:%d/%m %H:%M} | {res['volume']:>4} posts/h "
                      f"(x{res['ratio']:.0f}) {_ICON[res['level']]} {res['level']}")
            for a in res["alerts"]:
                if verbose:
                    print(f"      -> {a}")

            trig = res["trigger"]
            if trig is not None and n_triggers < max_triggers:
                n_triggers += 1
                if verbose:
                    print(f"      [DECLENCHEMENT] agents LLM sur {trig.event_id} "
                          f"(connaissance arretee a {ts:%d/%m %H:%M})")
                report = self.analysis.analyze(trig)
                draft = self.riposte.draft(report)
                bundles.append(EventBundle(event=trig, report=report, riposte=draft))
                if verbose:
                    print(f"         narratif : {report.narratif_dominant} | "
                          f"riposte prete (validation humaine requise)")

            if hour_delay:
                time.sleep(hour_delay)

        if verbose:
            print("-" * 64 + f"\n[FIN] Rejeu termine — {n_triggers} declenchement(s) traite(s).\n")

        return PipelineResult(provider=self.app.llm.provider,
                              n_events_detected=len(bundles), bundles=bundles)

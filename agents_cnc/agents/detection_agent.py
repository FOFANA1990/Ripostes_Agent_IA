"""
detection_agent.py — Agent 1 : Veille / Détection (DÉTERMINISTE, pas de LLM).

Deux modes, MÊME logique de seuils :
  - batch    : analyse tout le corpus d'un coup (DetectionAgent.run) ;
  - streaming : alimenté heure par heure par le moteur de rejeu (voir streaming.py).

Un emballement se MESURE (volume, vitesse) ; il ne s'invente pas. La fonction
`assemble_event` calcule les faits d'un événement à partir d'une fenêtre de posts
— ces faits servent ensuite d'ancrage aux agents LLM.
"""
from __future__ import annotations

import logging

import pandas as pd

from config import DetectionConfig
from data_loader import extract_handle, narrative_hits
from schemas import Amplifier, DetectedEvent, SourcePost

logger = logging.getLogger("agents_cnc.detection")

_LEVEL_ORDER = {"faible": 1, "montee": 2, "crise": 3}


def classify_level(ratio: float, cfg: DetectionConfig) -> str | None:
    """Niveau d'alerte en fonction du rapport volume/ligne de base."""
    if ratio >= cfg.factor_crise:
        return "crise"
    if ratio >= cfg.factor_montee:
        return "montee"
    if ratio >= cfg.factor_faible:
        return "faible"
    return None


def _source_post(lookup_df: pd.DataFrame, url: str, rt: int) -> SourcePost:
    """Retrouve l'auteur et le texte d'un post source retweeté (appariement d'URL)."""
    match = lookup_df[lookup_df["Url"].astype(str) == url]
    if len(match):
        row = match.iloc[0]
        return SourcePost(post_id=str(row.get("postID", "")), url=url,
                          author=str(row.get("Author", "")), retweets=rt,
                          text=str(row.get("Full Text", ""))[:280])
    return SourcePost(post_id="", url=url, author=extract_handle(url) or "", retweets=rt, text="")


def assemble_event(window: pd.DataFrame, lookup_df: pd.DataFrame, cfg: DetectionConfig, *,
                   level: str, peak_ts, peak_vol: int, peak_ratio: float,
                   window_start, window_end) -> DetectedEvent:
    """
    Construit un DetectedEvent à partir des posts d'une fenêtre.

    `window`    : posts connus de l'événement (en streaming = uniquement le passé).
    `lookup_df` : référentiel pour retrouver le texte des posts sources.
    """
    rts = window[window["X Repost of"].notna()].copy()
    rts["cible"] = rts["X Repost of"].map(extract_handle)
    amp_counts = rts["cible"].value_counts().head(cfg.max_amplifiers)
    amplifiers = [Amplifier(handle=str(h), reprises=int(c)) for h, c in amp_counts.items() if h]

    src_counts = rts["X Repost of"].astype(str).value_counts().head(cfg.max_source_posts)
    source_posts = [_source_post(lookup_df, url, int(c)) for url, c in src_counts.items()]

    sentiment_counts = {str(k): int(v) for k, v in window["Sentiment"].value_counts().items()}

    return DetectedEvent(
        event_id=f"EVT-{pd.Timestamp(peak_ts):%Y%m%d-%H}",
        level=level,
        window_start=str(window_start),
        window_end=str(window_end),
        peak_hour=str(peak_ts),
        peak_volume=int(peak_vol),
        total_volume=int(len(window)),
        velocity_factor=round(float(peak_ratio), 1),
        trigger_reason=(f"Volume de {int(peak_vol)} posts/h au pic, soit {round(float(peak_ratio),1)}x "
                        f"la ligne de base — seuil '{level}' franchi."),
        top_amplifiers=amplifiers,
        source_posts=source_posts,
        sentiment_counts=sentiment_counts,
        narrative_hits=narrative_hits(window["message_normalizer"], cfg.resolved_narratives()),
    )


class DetectionAgent:
    """Agent de veille déterministe — mode batch (corpus complet)."""

    def __init__(self, config: DetectionConfig):
        self.cfg = config

    def run(self, df: pd.DataFrame) -> list[DetectedEvent]:
        hourly = df.set_index("Date").resample("h").size().rename("volume")
        if hourly.empty:
            return []
        baseline = (hourly.rolling(self.cfg.baseline_window_h, min_periods=1).median()
                    .clip(lower=self.cfg.min_baseline))
        ratio = hourly / baseline
        level = ratio.apply(lambda r: classify_level(r, self.cfg))

        events = self._group_events(hourly, ratio, level)
        out = []
        for ev in events:
            peak_ts, peak_vol, peak_ratio, _ = max(ev["hours"], key=lambda h: h[1])
            worst = max((h[3] for h in ev["hours"]), key=lambda l: _LEVEL_ORDER[l])
            start, end = ev["start"], ev["end"] + pd.Timedelta(hours=1)
            window = df[(df["Date"] >= start) & (df["Date"] < end)]
            out.append(assemble_event(window, df, self.cfg, level=worst, peak_ts=peak_ts,
                                      peak_vol=peak_vol, peak_ratio=peak_ratio,
                                      window_start=start, window_end=end))
        out.sort(key=lambda e: (_LEVEL_ORDER[e.level], e.peak_volume), reverse=True)
        logger.info("Détection (batch) : %d événement(s).", len(out))
        return out

    def _group_events(self, hourly, ratio, level) -> list[dict]:
        events, current = [], None
        for ts, lv in level.items():
            if lv is None:
                if current:
                    events.append(current); current = None
                continue
            if current is None:
                current = {"start": ts, "end": ts, "hours": []}
            current["end"] = ts
            current["hours"].append((ts, int(hourly[ts]), float(ratio[ts]), lv))
        if current:
            events.append(current)
        return events

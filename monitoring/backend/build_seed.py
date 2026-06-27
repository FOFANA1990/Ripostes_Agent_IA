"""
build_seed.py — Genere monitoring_seed.json a partir du pipeline d'agents.

Rejoue le corpus, collecte le flux d'alertes, les evenements declenches (avec
fiche + riposte), la timeline horaire et les KPIs. Le backend FastAPI sert
ensuite ce fichier (+ gere l'etat des decisions).

Test REEL (non-mock) :
    export GOOGLE_API_KEY=...        # ou MISTRAL_API_KEY=...
    python build_seed.py --provider gemini       # ou --provider mistral
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Rend le paquet d'agents importable
AGENTS = Path(__file__).resolve().parents[2] / "agents_cnc"
sys.path.insert(0, str(AGENTS))

import pandas as pd  # noqa: E402
from config import load_config, get_chat_model  # noqa: E402
from data_loader import load_corpus  # noqa: E402
from streaming import StreamingDetector  # noqa: E402
from triggers import TriggerPolicy  # noqa: E402
from agents import AnalysisAgent, RiposteAgent  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Genere le seed du monitoring.")
    p.add_argument("--provider", choices=["gemini", "mistral", "mock"], default=None,
                   help="Surcharge llm.provider (test reel = gemini/mistral)")
    p.add_argument("--max-events", type=int, default=6)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    corpus = AGENTS.parent / "data.xlsx"
    app = load_config(AGENTS / "config.yaml", provider_override=args.provider)
    print(f"[seed] fournisseur LLM = {app.llm.provider}")
    df = load_corpus(corpus)

    detector = StreamingDetector(app.detection, TriggerPolicy(app.trigger))
    model = get_chat_model(app)
    analysis, riposte = AnalysisAgent(model), RiposteAgent(model)

    df = df.copy()
    df["__hour"] = df["Date"].dt.floor("h")
    groups = dict(tuple(df.groupby("__hour")))
    clock = pd.date_range(df["__hour"].min(), df["__hour"].max(), freq="h")
    empty = df.iloc[0:0]

    alerts, events, timeline = [], [], []
    for ts in clock:
        res = detector.feed_hour(ts, groups.get(ts, empty))
        timeline.append({"hour": ts.isoformat(), "volume": int(res["volume"])})
        for a in res["alerts"]:
            alerts.append({"ts": ts.isoformat(), "level": res["level"] or "faible", "message": a})
        trig = res["trigger"]
        if trig is not None and len(events) < args.max_events:
            try:
                report = analysis.analyze(trig)
                draft = riposte.draft(report)
            except Exception as e:                       # ex. 503 transitoire cote LLM
                print(f"[seed] !! {trig.event_id} ignore (erreur LLM : {type(e).__name__})")
                continue
            events.append({
                "event": json.loads(trig.model_dump_json()),
                "report": json.loads(report.model_dump_json()),
                "riposte": json.loads(draft.model_dump_json()),
                "detected_at": ts.isoformat(),
                "status": "pending",
            })
            print(f"[seed] {trig.event_id} traite ({len(events)}/{args.max_events})")

    kpis = {
        "events_detected": int(sum(1 for a in alerts if "OUVERTURE" in a["message"])),
        "pending_validation": len(events),
        "reach_cumule": int(df["Reach"].sum()),
        "peak_volume": int(max(t["volume"] for t in timeline)),
        "total_posts": int(len(df)),
        "negative_share_pct": round(float((df["Sentiment"] == "negative").mean() * 100), 1),
    }
    seed = {"generated_provider": app.llm.provider, "kpis": kpis,
            "timeline": timeline, "alerts": alerts[-60:], "events": events}
    out = Path(__file__).resolve().parent / "monitoring_seed.json"
    out.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[seed] ecrit: {out} | events={len(events)} alerts={len(alerts)} timeline={len(timeline)}")


if __name__ == "__main__":
    main()

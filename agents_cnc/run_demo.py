"""
run_demo.py — Point d'entrée CLI (mode batch : tout le corpus d'un coup).

Exemples
--------
    python run_demo.py --input ../data.xlsx                       # config.yaml
    python run_demo.py --input ../data.xlsx --provider gemini     # surcharge le provider
    python run_demo.py --input ../data.xlsx --config config.yaml --max-events 2
"""
from __future__ import annotations

import argparse
from pathlib import Path

from config import load_config, logger
from data_loader import load_corpus
from orchestrator import Orchestrator


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Chaîne d'agents CNC (batch).")
    p.add_argument("--input", type=Path, required=True, help="Corpus .xlsx/.csv")
    p.add_argument("--config", type=Path, default=Path("config.yaml"))
    p.add_argument("--provider", choices=["gemini", "mistral", "mock"], default=None,
                   help="Surcharge llm.provider de la config")
    p.add_argument("--max-events", type=int, default=3)
    p.add_argument("--output", type=Path, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    app = load_config(args.config, provider_override=args.provider)
    output = args.output or Path(app.runtime.output_dir) / "resultats_agents.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    df = load_corpus(args.input)
    result = Orchestrator(app).run(df, max_events=args.max_events)

    output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    logger.info("Résultats écrits dans %s", output.resolve())

    print("\n" + "=" * 64)
    print(f"FOURNISSEUR : {result.provider}   |   ÉVÉNEMENTS DÉTECTÉS : {result.n_events_detected}")
    print("=" * 64)
    for b in result.bundles:
        e = b.event
        print(f"\n● {e.event_id}  [{e.level.upper()}]  pic {e.peak_hour} "
              f"({e.peak_volume} posts/h, x{e.velocity_factor})")
        print(f"  Amplificateurs : {', '.join(a.handle for a in e.top_amplifiers[:5])}")
        print(f"  Narratif       : {b.report.narratif_dominant}")
        print(f"  Riposte (angle): {b.riposte.angle}")
    print("\n" + "=" * 64)


if __name__ == "__main__":
    main()

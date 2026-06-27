"""
run_stream.py — Démonstration TEMPS RÉEL (rejeu du dataset).

Fait défiler le corpus heure par heure comme si les posts arrivaient en direct.
La détection ne voit que le passé ; le déclenchement suit la `TriggerPolicy`
(section `trigger` de config.yaml).

Exemples
--------
    python run_stream.py --input ../data.xlsx
    python run_stream.py --input ../data.xlsx --provider mistral --max-triggers 2
    python run_stream.py --input ../data.xlsx --hour-delay 0.02
"""
from __future__ import annotations

import argparse
from pathlib import Path

from config import load_config, logger
from data_loader import load_corpus
from streaming import StreamSession


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Rejeu temps réel de la chaîne d'agents CNC.")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--config", type=Path, default=Path("config.yaml"))
    p.add_argument("--provider", choices=["gemini", "mistral", "mock"], default=None)
    p.add_argument("--hour-delay", type=float, default=0.0,
                   help="Secondes réelles par heure simulée (0 = aussi vite que possible)")
    p.add_argument("--max-triggers", type=int, default=3)
    p.add_argument("--output", type=Path, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    app = load_config(args.config, provider_override=args.provider)
    output = args.output or Path(app.runtime.output_dir) / "resultats_stream.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    df = load_corpus(args.input)
    result = StreamSession(app).run(df, hour_delay=args.hour_delay, max_triggers=args.max_triggers)

    output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    logger.info("Résultats du rejeu écrits dans %s", output.resolve())


if __name__ == "__main__":
    main()

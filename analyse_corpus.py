#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyse_corpus.py
=================

Analyse descriptive d'un corpus de posts X/Twitter (export social listening)
autour de la polémique CNC.

Objectif (phase 1) : répondre, à partir du dataset, aux 5 questions
    - QUI a lancé / amplifié ?
    - COMMENT ?
    - POURQUOI ça a pris ?
    - DEPUIS QUAND ?
    - À QUELLE VITESSE ?

Le script ne suppose rien : tous les indicateurs sont calculés à partir
des données. Les résultats sont écrits dans un dossier de sortie
(JSON + CSV) et résumés dans la console.

Usage
-----
    python analyse_corpus.py --input data.xlsx --outdir resultats

Bonnes pratiques appliquées : typage, dataclasses, logging, pathlib,
fonctions pures et testables, point d'entrée protégé par __main__.

Dépendances : pandas, numpy, openpyxl
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("analyse_corpus")

# Valeur de "Engagement Type" pour un message original (premier maillon).
# Dans le dataset brut, ce champ est VIDE pour un message original.
ORIGINAL_LABEL = "ORIGINAL"

# Mots-clés narratifs recherchés dans `message_normalizer` (déjà normalisé :
# minuscules, sans accents). Regroupés par angle de cadrage.
NARRATIVES: dict[str, list[str]] = {
    "argent_public": ["subvention", "subventionne", "argent public", "finance", "millions", "contribuable", "impot"],
    "anti_france": ["insultant", "anti france", "anti-france", "france", "drapeau"],
    "elites_filiation": ["fils de", "frere de", "duhamel", "saint cricq", "gavras"],
    "politique": ["gauche", "droite", "rn", "lfi", "macron", "bellamy", "marechal"],
    "censure_liberte": ["censure", "liberte", "art", "creation"],
}


# --------------------------------------------------------------------------- #
# Modèle de résultats
# --------------------------------------------------------------------------- #

@dataclass
class AnalysisResult:
    """Conteneur sérialisable de tous les indicateurs calculés."""
    chiffres_cles: dict[str, Any] = field(default_factory=dict)
    repartition_engagement: dict[str, float] = field(default_factory=dict)
    repartition_sentiment: dict[str, float] = field(default_factory=dict)
    primo_diffuseurs: list[dict[str, Any]] = field(default_factory=list)
    amplificateurs: list[dict[str, Any]] = field(default_factory=list)
    timeline_jour: list[dict[str, Any]] = field(default_factory=list)
    vitesse: dict[str, Any] = field(default_factory=dict)
    top_hashtags: list[dict[str, Any]] = field(default_factory=list)
    narratifs: dict[str, int] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Chargement & nettoyage
# --------------------------------------------------------------------------- #

def load_dataset(path: Path) -> pd.DataFrame:
    """Charge le fichier (.xlsx ou .csv) et renvoie un DataFrame brut."""
    logger.info("Chargement du dataset : %s", path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    elif path.suffix.lower() in {".csv", ".tsv"}:
        sep = "\t" if path.suffix.lower() == ".tsv" else ","
        df = pd.read_csv(path, sep=sep)
    else:
        raise ValueError(f"Format non supporté : {path.suffix}")
    logger.info("Dataset chargé : %d lignes, %d colonnes", *df.shape)
    return df


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise les types utiles à l'analyse (dates, engagement, numériques)."""
    df = df.copy()

    # Dates : on retire un éventuel ".0" final puis on parse.
    df["Date"] = pd.to_datetime(
        df["Date"].astype(str).str.replace(r"\.0$", "", regex=True),
        errors="coerce",
    )

    # Engagement Type vide -> ORIGINAL (premier maillon de la chaîne).
    df["Engagement Type"] = (
        df["Engagement Type"].fillna(ORIGINAL_LABEL).replace("", ORIGINAL_LABEL)
    )

    # Colonnes numériques : coercition robuste.
    for col in ["Likes", "Comments", "Shares", "Impressions", "Reach",
                "X Followers", "X Following", "X Posts"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    n_drop = df["Date"].isna().sum()
    if n_drop:
        logger.warning("%d lignes sans date valide ignorées dans la timeline", n_drop)
    return df


# --------------------------------------------------------------------------- #
# Indicateurs
# --------------------------------------------------------------------------- #

def key_figures(df: pd.DataFrame) -> dict[str, Any]:
    """Chiffres clés globaux du corpus."""
    d0, d1 = df["Date"].min(), df["Date"].max()
    return {
        "total_posts": int(len(df)),
        "auteurs_uniques": int(df["Author"].nunique()),
        "date_debut": str(d0),
        "date_fin": str(d1),
        "duree_jours": int((d1 - d0).days),
        "reach_cumule": int(df["Reach"].sum()),
        "impressions_cumulees": int(df["Impressions"].sum()),
        "part_retweets_pct": round(
            (df["Engagement Type"] == "RETWEET").mean() * 100, 1
        ),
    }


def distribution(df: pd.DataFrame, col: str) -> dict[str, float]:
    """Répartition en pourcentage d'une colonne catégorielle."""
    return (df[col].value_counts(normalize=True, dropna=False) * 100).round(1).to_dict()


def reconstruct_cascades(df: pd.DataFrame, top: int = 10) -> tuple[list[dict], list[dict]]:
    """
    Reconstruit les cascades de diffusion.

    - primo-diffuseurs : messages ORIGINAUX ayant généré le plus de retweets
      (appariement Url du message original <-> 'X Repost of' des retweets).
    - amplificateurs : comptes les plus retweetés, pondérés par l'audience.
    """
    rt_counts = df["X Repost of"].dropna().astype(str).value_counts()

    originals = df[df["Engagement Type"] == ORIGINAL_LABEL].copy()
    originals["rt_recus"] = (
        originals["Url"].astype(str).map(rt_counts).fillna(0).astype(int)
    )
    primo = (
        originals.sort_values("rt_recus", ascending=False)
        .head(top)[["Author", "rt_recus", "Reach", "X Followers", "X Verified", "Date", "Url"]]
        .rename(columns={"X Followers": "followers", "X Verified": "verified"})
    )
    primo_records = [
        {
            "auteur": r.Author,
            "retweets_generes": int(r.rt_recus),
            "reach": int(r.Reach),
            "followers": int(r.followers),
            "certifie": bool(r.verified),
            "date": str(r.Date),
            "url": r.Url,
        }
        for r in primo.itertuples(index=False)
    ]

    # Amplificateurs : comptes les plus retweetés (toutes cascades confondues).
    amp = (
        df[df["X Repost of"].notna()]
        .assign(cible=lambda x: x["X Repost of"].astype(str).str.extract(r"twitter\.com/([^/]+)/")[0])
        .groupby("cible")
        .size()
        .sort_values(ascending=False)
        .head(top)
    )
    amp_records = [{"compte_retweete": k, "nb_reprises": int(v)} for k, v in amp.items()]
    return primo_records, amp_records


def build_timeline(df: pd.DataFrame, freq: str = "D") -> pd.DataFrame:
    """Volume de posts agrégé par pas de temps (D = jour, H = heure)."""
    ts = (
        df.dropna(subset=["Date"])
        .set_index("Date")
        .resample(freq)
        .size()
        .rename("volume")
        .reset_index()
    )
    ts["volume_cumule"] = ts["volume"].cumsum()
    return ts


def velocity_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """
    Indicateurs de vitesse de propagation :
    - pic horaire (date + volume),
    - délai entre le 1er post et le pic,
    - temps de doublement moyen sur la phase de montée.
    """
    hourly = (
        df.dropna(subset=["Date"]).set_index("Date").resample("H").size().rename("v")
    )
    if hourly.empty:
        return {}

    peak_time = hourly.idxmax()
    peak_val = int(hourly.max())
    start = df["Date"].min()
    delai_h = round((peak_time - start).total_seconds() / 3600, 1)

    # Temps de doublement sur la montée (du début jusqu'au pic).
    montee = hourly.loc[:peak_time].cumsum()
    montee = montee[montee > 0]
    if len(montee) > 2:
        t = np.arange(len(montee))
        # régression log-linéaire : log(cumul) = a*t + b -> taux de croissance a
        coef = np.polyfit(t, np.log(montee.values), 1)[0]
        doubling_h = round(np.log(2) / coef, 1) if coef > 0 else None
    else:
        doubling_h = None

    vol_moy = df.dropna(subset=["Date"]).set_index("Date").resample("D").size().mean()
    return {
        "pic_horaire_date": str(peak_time),
        "pic_horaire_volume": peak_val,
        "delai_debut_vers_pic_h": float(delai_h),
        "temps_doublement_h": float(doubling_h) if doubling_h is not None else None,
        "volume_moyen_par_jour": round(float(vol_moy), 1),
    }


def top_hashtags(df: pd.DataFrame, top: int = 15) -> list[dict[str, Any]]:
    """Hashtags les plus fréquents."""
    tags = (
        df["Hashtags"].dropna().astype(str)
        .str.lower().str.split(r"[,\s]+")
        .explode().str.strip()
    )
    tags = tags[tags.str.startswith("#") & (tags.str.len() > 1)]
    vc = tags.value_counts().head(top)
    return [{"hashtag": k, "occurrences": int(v)} for k, v in vc.items()]


def narrative_counts(df: pd.DataFrame) -> dict[str, int]:
    """Compte les posts contenant les mots-clés de chaque angle narratif."""
    text = df["message_normalizer"].fillna("").astype(str)
    out: dict[str, int] = {}
    for angle, keywords in NARRATIVES.items():
        mask = np.zeros(len(text), dtype=bool)
        for kw in keywords:
            mask |= text.str.contains(kw, regex=False)
        out[angle] = int(mask.sum())
    return dict(sorted(out.items(), key=lambda kv: kv[1], reverse=True))


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def analyse(df: pd.DataFrame) -> tuple[AnalysisResult, pd.DataFrame]:
    """Exécute toute la chaîne d'analyse et renvoie les résultats."""
    primo, amp = reconstruct_cascades(df)
    timeline = build_timeline(df, freq="D")
    res = AnalysisResult(
        chiffres_cles=key_figures(df),
        repartition_engagement=distribution(df, "Engagement Type"),
        repartition_sentiment=distribution(df, "Sentiment"),
        primo_diffuseurs=primo,
        amplificateurs=amp,
        timeline_jour=[
            {"date": str(r.Date.date()), "volume": int(r.volume),
             "volume_cumule": int(r.volume_cumule)}
            for r in timeline.itertuples(index=False)
        ],
        vitesse=velocity_metrics(df),
        top_hashtags=top_hashtags(df),
        narratifs=narrative_counts(df),
    )
    return res, timeline


def export_results(res: AnalysisResult, timeline: pd.DataFrame, outdir: Path) -> None:
    """Écrit les résultats (JSON complet + CSV de la timeline)."""
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "analyse.json").write_text(
        json.dumps(asdict(res), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    timeline.to_csv(outdir / "timeline.csv", index=False)
    logger.info("Résultats exportés dans : %s", outdir.resolve())


def print_summary(res: AnalysisResult) -> None:
    """Résumé lisible en console."""
    k = res.chiffres_cles
    print("\n" + "=" * 60)
    print("SYNTHÈSE DE L'ANALYSE DESCRIPTIVE")
    print("=" * 60)
    print(f"Posts            : {k['total_posts']:,}")
    print(f"Auteurs uniques  : {k['auteurs_uniques']:,}")
    print(f"Période          : {k['date_debut']}  ->  {k['date_fin']}  ({k['duree_jours']} j)")
    print(f"Reach cumulé     : {k['reach_cumule']:,}")
    print(f"Part de retweets : {k['part_retweets_pct']} %")
    print(f"\nEngagement       : {res.repartition_engagement}")
    print(f"Sentiment        : {res.repartition_sentiment}")
    print(f"Vitesse          : {res.vitesse}")
    print("\nTop 5 primo-diffuseurs (originaux les + repris) :")
    for p in res.primo_diffuseurs[:5]:
        print(f"  - {p['auteur']:<22} {p['retweets_generes']:>5} RT  | reach {p['reach']:,}")
    print("\nTop 5 amplificateurs (comptes les + retweetés) :")
    for a in res.amplificateurs[:5]:
        print(f"  - {a['compte_retweete']:<22} {a['nb_reprises']:>5} reprises")
    print(f"\nNarratifs (posts concernés) : {res.narratifs}")
    print("=" * 60 + "\n")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyse descriptive du corpus CNC.")
    p.add_argument("--input", type=Path, required=True, help="Fichier .xlsx/.csv du corpus")
    p.add_argument("--outdir", type=Path, default=Path("resultats"), help="Dossier de sortie")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    df = clean_dataset(load_dataset(args.input))
"""
data_loader.py — Chargement et nettoyage du corpus.

Source unique de verite pour la lecture des donnees : tous les agents
travaillent sur le DataFrame produit ici (colonnes typees, dates parsees).

`DEFAULT_NARRATIVES` = mots-cles narratifs par defaut du domaine. Ils peuvent
etre surcharges via `config.yaml` (section detection.narratives).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger("agents_cnc.data")

ORIGINAL_LABEL = "ORIGINAL"

# Mots-cles narratifs par defaut (sur message_normalizer : minuscules, sans accents).
DEFAULT_NARRATIVES: dict[str, list[str]] = {
    "argent_public": ["subvention", "subventionne", "argent public", "finance", "millions", "contribuable", "impot"],
    "clivage_politique": ["gauche", "droite", "rn", "lfi", "macron", "bellamy", "marechal"],
    "censure_liberte": ["censure", "liberte", "art", "creation"],
    "anti_france": ["insultant", "anti france", "anti-france", "drapeau"],
    "elites_filiation": ["fils de", "frere de", "duhamel", "saint cricq", "gavras"],
}

_HANDLE_RE = re.compile(r"twitter\.com/([^/]+)/")


def load_corpus(path):
    """Charge et nettoie le corpus (.xlsx/.csv). Renvoie un DataFrame pret a l'emploi."""
    path = Path(path)
    logger.info("Chargement du corpus : %s", path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path, sep="\t" if path.suffix.lower() == ".tsv" else ",")

    df["Date"] = pd.to_datetime(
        df["Date"].astype(str).str.replace(r"\.0$", "", regex=True), errors="coerce"
    )
    df["Engagement Type"] = df["Engagement Type"].fillna(ORIGINAL_LABEL).replace("", ORIGINAL_LABEL)
    for col in ["Likes", "Comments", "Shares", "Impressions", "Reach", "X Followers", "X Following", "X Posts"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    n_bad = int(df["Date"].isna().sum())
    if n_bad:
        logger.warning("%d lignes sans date valide retirees.", n_bad)
        df = df.dropna(subset=["Date"])

    df = df.sort_values("Date").reset_index(drop=True)
    logger.info("Corpus pret : %d posts du %s au %s", len(df), df["Date"].min(), df["Date"].max())
    return df


def extract_handle(repost_url):
    """Extrait le pseudo cible d'une URL de retweet (X Repost of)."""
    if not isinstance(repost_url, str):
        return None
    m = _HANDLE_RE.search(repost_url)
    return m.group(1) if m else None


def narrative_hits(texts, narratives=None):
    """Compte, par angle narratif, le nombre de posts contenant un mot-cle."""
    narratives = narratives or DEFAULT_NARRATIVES
    t = texts.fillna("").astype(str)
    out = {}
    for angle, kws in narratives.items():
        mask = np.zeros(len(t), dtype=bool)
        for kw in kws:
            mask = mask | t.str.contains(kw, regex=False)
        out[angle] = int(mask.sum())
    return out

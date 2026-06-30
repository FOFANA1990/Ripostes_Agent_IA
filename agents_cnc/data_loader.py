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
import unicodedata
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

_TWEETCLAW_COLUMNS = {
    "date": ["createdAt", "created_at", "date", "published_at"],
    "text": ["text", "fullText", "full_text", "content"],
    "author": ["authorUsername", "author_username", "username", "screenName", "author"],
    "author_id": ["authorId", "author_id", "userId", "user_id"],
    "post_id": ["id", "tweetId", "tweet_id", "postID", "post_id"],
    "url": ["url", "tweetUrl", "tweet_url", "permalink"],
    "likes": ["likeCount", "likes"],
    "comments": ["replyCount", "replies", "comments"],
    "retweets": ["retweetCount", "retweets", "shares"],
    "quotes": ["quoteCount", "quotes"],
    "impressions": ["viewCount", "views", "impressions"],
    "reach": ["reach"],
    "followers": ["authorFollowers", "followers", "followerCount"],
    "following": ["authorFollowing", "following", "followingCount"],
    "posts": ["authorStatuses", "statusesCount", "posts"],
    "sentiment": ["sentiment", "Sentiment"],
}


def load_corpus(path):
    """Charge et nettoie le corpus (.xlsx/.csv). Renvoie un DataFrame pret a l'emploi."""
    path = Path(path)
    logger.info("Chargement du corpus : %s", path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path, sep="\t" if path.suffix.lower() == ".tsv" else ",")

    df = _normalize_tweetclaw_export(df)

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


def _normalize_tweetclaw_export(df: pd.DataFrame) -> pd.DataFrame:
    """Map a TweetClaw CSV export to the corpus columns used by the agents."""
    if "Date" in df.columns:
        return df
    date_col = _first_column(df, _TWEETCLAW_COLUMNS["date"])
    text_col = _first_column(df, _TWEETCLAW_COLUMNS["text"])
    if not date_col or not text_col:
        return df

    out = pd.DataFrame(index=df.index)
    text = df[text_col].fillna("").astype(str)
    author = _clean_handle(_column_or_empty(df, _TWEETCLAW_COLUMNS["author"]))
    post_id = _column_or_empty(df, _TWEETCLAW_COLUMNS["post_id"]).astype(str)

    out["Date"] = df[date_col]
    out["Full Text"] = text
    out["message_normalizer"] = text.map(_normalize_message)
    out["Author"] = author
    out["X Author ID"] = _column_or_empty(df, _TWEETCLAW_COLUMNS["author_id"])
    out["postID"] = post_id
    out["Url"] = _url_series(df, author, post_id)
    out["Engagement Type"] = _column_or_default(df, ["engagementType", "type"], ORIGINAL_LABEL)
    out["X Repost of"] = _column_or_default(df, ["repostOf", "repost_of", "retweetedUrl"], "")
    out["Sentiment"] = _column_or_default(df, _TWEETCLAW_COLUMNS["sentiment"], "unknown")
    out["Likes"] = _numeric_column(df, _TWEETCLAW_COLUMNS["likes"])
    out["Comments"] = _numeric_column(df, _TWEETCLAW_COLUMNS["comments"])
    out["Shares"] = (
        _numeric_column(df, _TWEETCLAW_COLUMNS["retweets"])
        + _numeric_column(df, _TWEETCLAW_COLUMNS["quotes"])
    )
    out["Impressions"] = _numeric_column(df, _TWEETCLAW_COLUMNS["impressions"])
    out["Reach"] = _numeric_column(df, _TWEETCLAW_COLUMNS["reach"])
    out["X Followers"] = _numeric_column(df, _TWEETCLAW_COLUMNS["followers"])
    out["X Following"] = _numeric_column(df, _TWEETCLAW_COLUMNS["following"])
    out["X Posts"] = _numeric_column(df, _TWEETCLAW_COLUMNS["posts"])
    return out


def _first_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _column_or_empty(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
    return _column_or_default(df, candidates, "")


def _column_or_default(df: pd.DataFrame, candidates: list[str], default: str) -> pd.Series:
    col = _first_column(df, candidates)
    if col:
        return df[col].fillna(default)
    return pd.Series(default, index=df.index)


def _numeric_column(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
    col = _first_column(df, candidates)
    if not col:
        return pd.Series(0, index=df.index)
    return pd.to_numeric(df[col], errors="coerce").fillna(0)


def _clean_handle(values: pd.Series) -> pd.Series:
    return values.fillna("").astype(str).str.lstrip("@")


def _url_series(df: pd.DataFrame, author: pd.Series, post_id: pd.Series) -> pd.Series:
    url_col = _first_column(df, _TWEETCLAW_COLUMNS["url"])
    if url_col:
        urls = df[url_col].fillna("").astype(str)
    else:
        urls = pd.Series("", index=df.index)
    missing = urls.str.strip() == ""
    built = "https://x.com/" + author.astype(str) + "/status/" + post_id.astype(str)
    urls.loc[missing] = built.loc[missing]
    return urls


def _normalize_message(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return ascii_text.lower()


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

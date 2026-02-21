"""Normalize ingested data to canonical schema."""

import hashlib
import uuid

import pandas as pd

from pt_insights_os.config import PII_SALT
from pt_insights_os.io.ingest import CANONICAL_COLUMNS
from pt_insights_os.logging_config import setup_logging

logger = setup_logging()

# Map common alternative column names to canonical names
COLUMN_ALIASES = {
    "id": "post_id",
    "message": "text",
    "content": "text",
    "body": "text",
    "timestamp": "created_at",
    "date": "created_at",
    "created_time": "created_at",
    "time": "created_at",
    "user": "author",
    "username": "author",
    "author_name": "author",
    "from": "author",
    "name": "author",
    "permalink": "url",
    "link": "url",
    "likes": "reactions",
    "reaction_count": "reactions",
    "replies": "reply_count",
    "num_replies": "reply_count",
    "has_media": "media_flag",
    "media": "media_flag",
    "media_type": "media_flag",
}


def hash_author(author: str) -> str:
    """Hash author name with salt for privacy."""
    if not author or pd.isna(author):
        return ""
    return hashlib.sha256(f"{PII_SALT}:{author}".encode()).hexdigest()[:16]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to canonical names and ensure all canonical columns exist."""
    # Apply aliases
    rename_map = {}
    existing_cols = set(df.columns)
    for alias, canonical in COLUMN_ALIASES.items():
        if alias in existing_cols and canonical not in existing_cols:
            rename_map[alias] = canonical

    if rename_map:
        df = df.rename(columns=rename_map)

    # Ensure all canonical columns exist
    for col in CANONICAL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    return df


def generate_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Generate missing IDs."""
    # Generate post_id if missing
    mask = df["post_id"].isna() | (df["post_id"] == "") | (df["post_id"] == "None")
    if mask.any():
        df.loc[mask, "post_id"] = [f"p_{uuid.uuid4().hex[:12]}" for _ in range(mask.sum())]

    # Thread ID defaults to post_id if not set
    mask = df["thread_id"].isna() | (df["thread_id"] == "") | (df["thread_id"] == "None")
    if mask.any():
        df.loc[mask, "thread_id"] = df.loc[mask, "post_id"]

    return df


def normalize_types(df: pd.DataFrame) -> pd.DataFrame:
    """Cast columns to appropriate types."""
    # created_at → datetime
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

    # reactions → numeric
    if "reactions" in df.columns:
        df["reactions"] = pd.to_numeric(df["reactions"], errors="coerce").fillna(0).astype(int)

    # reply_count → numeric
    if "reply_count" in df.columns:
        df["reply_count"] = pd.to_numeric(df["reply_count"], errors="coerce").fillna(0).astype(int)

    # media_flag → boolean
    if "media_flag" in df.columns:
        df["media_flag"] = df["media_flag"].apply(
            lambda x: bool(x) if not pd.isna(x) and x != "" and x != "None" else False
        )

    return df


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Full normalization pipeline."""
    logger.info(f"Normalizing {len(df)} rows")

    df = normalize_columns(df)
    df = generate_ids(df)
    df = normalize_types(df)

    # Hash authors
    df["author_id_hash"] = df["author"].apply(hash_author)

    # Ensure text is string
    df["text"] = df["text"].fillna("").astype(str)

    # Keep only canonical columns + author_id_hash
    output_cols = CANONICAL_COLUMNS + ["author_id_hash"]
    df = df[[c for c in output_cols if c in df.columns]]

    logger.info(f"Normalized to {len(df)} rows, {len(df.columns)} columns")
    return df

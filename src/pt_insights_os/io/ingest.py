"""Ingest raw Facebook exports (CSV, JSON, NDJSON, HTML) into normalized DataFrames."""

import json
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from pt_insights_os.logging_config import setup_logging

logger = setup_logging()

CANONICAL_COLUMNS = [
    "post_id",
    "comment_id",
    "thread_id",
    "parent_id",
    "author",
    "created_at",
    "text",
    "reactions",
    "reply_count",
    "url",
    "media_flag",
]


def ingest_csv(path: Path) -> pd.DataFrame:
    """Ingest a CSV file."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def ingest_json(path: Path) -> pd.DataFrame:
    """Ingest a JSON file (array of objects or single object with a list field)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        # Find the first list-valued key
        for v in data.values():
            if isinstance(v, list):
                records = v
                break
        else:
            records = [data]
    else:
        records = [data]
    df = pd.DataFrame(records)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def ingest_ndjson(path: Path) -> pd.DataFrame:
    """Ingest a newline-delimited JSON file."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    df = pd.DataFrame(records)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def ingest_html(path: Path) -> pd.DataFrame:
    """Ingest an HTML Facebook export — extract post/comment blocks."""
    with open(path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    records = []
    # Try to find structured content blocks
    for div in soup.find_all(["div", "article", "p"]):
        text = div.get_text(strip=True)
        if text and len(text) > 10:
            records.append({"text": text})

    if not records:
        # Fallback: just extract all text
        text = soup.get_text(strip=True)
        if text:
            records.append({"text": text})

    df = pd.DataFrame(records)
    return df


def ingest_file(path: Path) -> pd.DataFrame:
    """Auto-detect format and ingest a single file."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return ingest_csv(path)
    elif suffix == ".json":
        return ingest_json(path)
    elif suffix == ".ndjson" or suffix == ".jsonl":
        return ingest_ndjson(path)
    elif suffix in (".html", ".htm"):
        return ingest_html(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")


def ingest_directory(raw_dir: Path) -> pd.DataFrame:
    """Ingest all supported files from a directory, concatenate into one DataFrame."""
    supported = {".csv", ".json", ".ndjson", ".jsonl", ".html", ".htm"}
    frames = []
    for path in sorted(raw_dir.iterdir()):
        if path.suffix.lower() in supported and not path.name.startswith("."):
            logger.info(f"Ingesting {path.name}")
            try:
                df = ingest_file(path)
                frames.append(df)
            except Exception as e:
                logger.warning(f"Failed to ingest {path.name}: {e}")

    if not frames:
        logger.warning("No files found to ingest")
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    combined = pd.concat(frames, ignore_index=True)
    return combined

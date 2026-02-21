"""Central configuration loaded from .env + defaults."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Paths
DUCKDB_PATH = Path(os.getenv("DUCKDB_PATH", "data/warehouse/pt_insights.duckdb"))
if not DUCKDB_PATH.is_absolute():
    DUCKDB_PATH = PROJECT_ROOT / DUCKDB_PATH

PARQUET_DIR = Path(os.getenv("PARQUET_DIR", "data/processed"))
if not PARQUET_DIR.is_absolute():
    PARQUET_DIR = PROJECT_ROOT / PARQUET_DIR

RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
if not RAW_DATA_DIR.is_absolute():
    RAW_DATA_DIR = PROJECT_ROOT / RAW_DATA_DIR

# Privacy
PII_SALT = os.getenv("PII_SALT", "default-dev-salt-change-me")
REDACTION_VERSION = int(os.getenv("REDACTION_VERSION", "1"))

# Feature flags
ENABLE_LLM_TAGGER = os.getenv("ENABLE_LLM_TAGGER", "false").lower() == "true"
ENABLE_PRESIDIO = os.getenv("ENABLE_PRESIDIO", "auto")

# Embeddings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "auto")

# Search
VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "auto")

# Ensure directories exist
for d in [DUCKDB_PATH.parent, PARQUET_DIR, RAW_DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

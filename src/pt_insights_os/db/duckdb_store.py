"""DuckDB storage layer."""

from pathlib import Path

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from pt_insights_os.config import DUCKDB_PATH, PARQUET_DIR
from pt_insights_os.logging_config import setup_logging

logger = setup_logging()

SCHEMA_SQL = Path(__file__).parent / "schema.sql"


def get_connection(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection."""
    path = db_path or DUCKDB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(path))
    return conn


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Initialize database schema."""
    sql = SCHEMA_SQL.read_text()
    # Strip SQL comment lines before splitting on semicolons
    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    cleaned = "\n".join(lines)
    for statement in cleaned.split(";"):
        statement = statement.strip()
        if statement:
            conn.execute(statement)
    logger.info("Schema initialized")


def upsert_posts(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    """Insert or replace posts. Returns number of rows affected."""
    if df.empty:
        return 0

    # Ensure columns match schema
    post_cols = [
        "post_id",
        "thread_id",
        "comment_id",
        "parent_id",
        "author_id_hash",
        "created_at",
        "text_redacted",
        "text_raw",
        "pii_spans",
        "redaction_version",
        "reactions",
        "reply_count",
        "url",
        "media_flag",
    ]
    for col in post_cols:
        if col not in df.columns:
            df[col] = None

    insert_df = df[post_cols].copy()

    # Delete existing rows by post_id for upsert
    post_ids = insert_df["post_id"].tolist()
    if post_ids:
        conn.execute(
            "DELETE FROM posts WHERE post_id IN (SELECT UNNEST(?))",
            [post_ids],
        )

    conn.execute("INSERT INTO posts SELECT * FROM insert_df")
    count = len(insert_df)
    logger.info(f"Upserted {count} posts")
    return count


def rebuild_threads(conn: duckdb.DuckDBPyConnection) -> int:
    """Rebuild threads table from posts."""
    conn.execute("DELETE FROM threads")
    conn.execute("""
        INSERT INTO threads (thread_id, author_id_hash, created_at, post_count,
                           participant_count, total_reactions, url)
        SELECT
            thread_id,
            MIN(author_id_hash) AS author_id_hash,
            MIN(created_at) AS created_at,
            COUNT(*) AS post_count,
            COUNT(DISTINCT author_id_hash) AS participant_count,
            SUM(COALESCE(reactions, 0)) AS total_reactions,
            MIN(url) AS url
        FROM posts
        GROUP BY thread_id
    """)
    result = conn.execute("SELECT COUNT(*) FROM threads").fetchone()
    count = result[0] if result else 0
    logger.info(f"Rebuilt {count} threads")
    return count


def export_parquet(conn: duckdb.DuckDBPyConnection, parquet_dir: Path | None = None) -> None:
    """Export key tables to Parquet."""
    out_dir = parquet_dir or PARQUET_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    for table in ["posts", "threads"]:
        df = conn.execute(f"SELECT * FROM {table}").fetchdf()
        if not df.empty:
            path = out_dir / f"{table}.parquet"
            table_arrow = pa.Table.from_pandas(df)
            pq.write_table(table_arrow, path)
            logger.info(f"Exported {table} to {path} ({len(df)} rows)")


def load_posts(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Load all posts as DataFrame."""
    return conn.execute("SELECT * FROM posts").fetchdf()


def load_threads(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Load all threads as DataFrame."""
    return conn.execute("SELECT * FROM threads").fetchdf()


def run_qa_check(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    """Run QA checks on the database. Returns list of check results."""
    import re
    from datetime import datetime

    checks = []

    # Check 1: No emails in redacted text
    posts_df = conn.execute("SELECT post_id, text_redacted FROM posts").fetchdf()
    email_pattern = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
    email_leaks = []
    for _, row in posts_df.iterrows():
        if row["text_redacted"] and email_pattern.search(str(row["text_redacted"])):
            email_leaks.append(row["post_id"])

    checks.append(
        {
            "check_name": "no_emails_in_redacted",
            "status": "pass" if not email_leaks else "fail",
            "details": f"Found {len(email_leaks)} posts with email leaks" if email_leaks else "OK",
        }
    )

    # Check 2: No phone numbers in redacted text
    phone_pattern = re.compile(
        r"(?<!\d)(?:\+?1[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.]?)\d{3}[\s\-.]?\d{4}(?!\d)"
    )
    phone_leaks = []
    for _, row in posts_df.iterrows():
        if row["text_redacted"] and phone_pattern.search(str(row["text_redacted"])):
            # Exclude redaction markers
            text = str(row["text_redacted"])
            cleaned = re.sub(r"\[[A-Z_]+_REDACTED\]", "", text)
            if phone_pattern.search(cleaned):
                phone_leaks.append(row["post_id"])

    checks.append(
        {
            "check_name": "no_phones_in_redacted",
            "status": "pass" if not phone_leaks else "fail",
            "details": f"Found {len(phone_leaks)} posts with phone leaks" if phone_leaks else "OK",
        }
    )

    # Store results
    import uuid

    now = datetime.now()
    for check in checks:
        conn.execute(
            "INSERT INTO qa_audit VALUES (?, ?, ?, ?, ?)",
            [
                f"qa_{uuid.uuid4().hex[:8]}",
                check["check_name"],
                check["status"],
                check["details"],
                now,
            ],
        )

    return checks

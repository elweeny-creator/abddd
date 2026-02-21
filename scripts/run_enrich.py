"""Run enrichment pipeline: taxonomy tagging, metrics, entity extraction."""

import sys
import uuid
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pt_insights_os.db.duckdb_store import get_connection, load_posts, load_threads
from pt_insights_os.enrich.entities import (
    classify_business_stage,
    classify_intent,
    classify_setting,
    extract_entities,
)
from pt_insights_os.enrich.metrics import compute_post_scores, compute_thread_scores
from pt_insights_os.logging_config import setup_logging
from pt_insights_os.taxonomy.tagger import get_tag_registry, tag_text

logger = setup_logging()


def ensure_enrichment_columns(conn) -> None:
    """Add enrichment columns to posts table if they don't exist."""
    enrichment_cols = {
        "actionable_density": "FLOAT",
        "burnout_signal_score": "FLOAT",
        "owner_relevance_score": "FLOAT",
        "intent_type": "VARCHAR",
        "business_stage": "VARCHAR",
        "setting_type": "VARCHAR",
    }
    existing = {
        row[0]
        for row in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='posts'"
        ).fetchall()
    }
    for col, dtype in enrichment_cols.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE posts ADD COLUMN {col} {dtype}")

    # Thread enrichment columns
    thread_cols = {
        "thread_quality_score": "FLOAT",
        "novelty_score": "FLOAT",
        "disagreement_score": "FLOAT",
        "actionable_density": "FLOAT",
        "owner_relevance_score": "FLOAT",
        "burnout_signal_score": "FLOAT",
    }
    existing_thread = {
        row[0]
        for row in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='threads'"
        ).fetchall()
    }
    for col, dtype in thread_cols.items():
        if col not in existing_thread:
            conn.execute(f"ALTER TABLE threads ADD COLUMN {col} {dtype}")


def main():
    conn = get_connection()

    # Ensure columns exist
    ensure_enrichment_columns(conn)

    # Load data
    posts_df = load_posts(conn)
    threads_df = load_threads(conn)

    if posts_df.empty:
        logger.warning("No posts found — run ingest first")
        return

    logger.info(f"Enriching {len(posts_df)} posts across {len(threads_df)} threads")

    # 1. Taxonomy tagging
    logger.info("Running taxonomy tagger")
    tag_registry = get_tag_registry()

    # Ensure tags table is populated
    tag_rows = []
    seen_tags = set()
    for tag_name, info in tag_registry.items():
        if info["tag_id"] not in seen_tags:
            tag_rows.append({
                "tag_id": info["tag_id"],
                "l1_domain": info["l1_domain"],
                "l2_subdomain": info["l2_subdomain"],
                "l3_tag": info["l3_tag"],
                "description": None,
            })
            seen_tags.add(info["tag_id"])

    if tag_rows:
        tags_df = pd.DataFrame(tag_rows)
        conn.execute("DELETE FROM tags")
        conn.execute("INSERT INTO tags SELECT * FROM tags_df")
        logger.info(f"Loaded {len(tag_rows)} tags into registry")

    # Tag each post
    all_assignments = []
    for _, post in posts_df.iterrows():
        text = post.get("text_redacted", "")
        assignments = tag_text(text)
        for a in assignments:
            a["post_id"] = post["post_id"]
            all_assignments.append(a)

    if all_assignments:
        assign_df = pd.DataFrame(all_assignments)
        assign_df = assign_df[["assignment_id", "post_id", "tag_id", "confidence", "source"]]
        conn.execute("DELETE FROM tag_assignments")
        conn.execute("INSERT INTO tag_assignments SELECT * FROM assign_df")
        logger.info(f"Created {len(all_assignments)} tag assignments")

    # 2. Entity extraction
    logger.info("Extracting entities")
    all_entities = []
    for _, post in posts_df.iterrows():
        text = post.get("text_redacted", "")
        entities = extract_entities(text, post["post_id"])
        all_entities.extend(entities)

    if all_entities:
        ent_df = pd.DataFrame(all_entities)
        conn.execute("DELETE FROM entities")
        conn.execute("INSERT INTO entities SELECT * FROM ent_df")
        logger.info(f"Extracted {len(all_entities)} entities")

    # 3. Compute post-level scores + classifications
    logger.info("Computing post scores")
    posts_df = compute_post_scores(posts_df)

    # Classify intent, business stage, setting
    posts_df["intent_type"] = posts_df["text_redacted"].apply(classify_intent)
    posts_df["business_stage"] = posts_df["text_redacted"].apply(classify_business_stage)
    posts_df["setting_type"] = posts_df["text_redacted"].apply(classify_setting)

    # Update posts with enrichment data
    for _, row in posts_df.iterrows():
        conn.execute("""
            UPDATE posts SET
                actionable_density = ?,
                burnout_signal_score = ?,
                owner_relevance_score = ?,
                intent_type = ?,
                business_stage = ?,
                setting_type = ?
            WHERE post_id = ?
        """, [
            row.get("actionable_density"),
            row.get("burnout_signal_score"),
            row.get("owner_relevance_score"),
            row.get("intent_type"),
            row.get("business_stage"),
            row.get("setting_type"),
            row["post_id"],
        ])

    # 4. Compute thread-level scores
    logger.info("Computing thread scores")
    threads_df = compute_thread_scores(posts_df, threads_df)

    for _, row in threads_df.iterrows():
        conn.execute("""
            UPDATE threads SET
                thread_quality_score = ?,
                novelty_score = ?,
                disagreement_score = ?,
                actionable_density = ?,
                owner_relevance_score = ?,
                burnout_signal_score = ?
            WHERE thread_id = ?
        """, [
            row.get("thread_quality_score"),
            row.get("novelty_score"),
            row.get("disagreement_score"),
            row.get("actionable_density"),
            row.get("owner_relevance_score"),
            row.get("burnout_signal_score"),
            row["thread_id"],
        ])

    logger.info("Enrichment pipeline complete")
    conn.close()


if __name__ == "__main__":
    main()

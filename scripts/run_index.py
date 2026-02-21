"""Build the search index from posts in DuckDB."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pt_insights_os.db.duckdb_store import get_connection, load_posts
from pt_insights_os.logging_config import setup_logging
from pt_insights_os.search.chunking import prepare_chunks
from pt_insights_os.search.index import VectorIndex, save_index_meta

logger = setup_logging()


def main():
    conn = get_connection()
    posts_df = load_posts(conn)

    if posts_df.empty:
        logger.warning("No posts found — run ingest first")
        return

    # Convert to list of dicts for chunking
    posts = posts_df.to_dict("records")
    logger.info(f"Preparing chunks from {len(posts)} posts")

    chunks = prepare_chunks(posts)
    logger.info(f"Created {len(chunks)} chunks")

    # Build index
    index = VectorIndex()
    index.build(chunks)

    # Save index
    index.save()

    # Save metadata to DuckDB
    save_index_meta(conn, index)

    conn.close()
    logger.info("Search index built successfully")


if __name__ == "__main__":
    main()

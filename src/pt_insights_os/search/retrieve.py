"""Retrieval layer — keyword + semantic search with source traceability."""

import re

import pandas as pd

from pt_insights_os.search.index import VectorIndex


def keyword_search(query: str, posts_df: pd.DataFrame, top_k: int = 10) -> list[dict]:
    """Simple keyword search over posts."""
    text_col = "text_redacted" if "text_redacted" in posts_df.columns else "text"

    # Build search terms
    terms = [t.strip().lower() for t in query.split() if len(t.strip()) > 2]
    if not terms:
        return []

    results = []
    for _, row in posts_df.iterrows():
        text = str(row.get(text_col, "")).lower()
        # Score = fraction of query terms found
        matches = sum(1 for t in terms if t in text)
        if matches > 0:
            score = matches / len(terms)
            results.append({
                "post_id": row["post_id"],
                "thread_id": row.get("thread_id", ""),
                "comment_id": row.get("comment_id"),
                "text": row.get(text_col, ""),
                "score": round(score, 3),
                "source": "keyword",
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def semantic_search(query: str, index: VectorIndex, top_k: int = 10) -> list[dict]:
    """Semantic search via vector index."""
    results = index.search(query, top_k=top_k)
    for r in results:
        r["source"] = "semantic"
    return results


def hybrid_search(
    query: str,
    posts_df: pd.DataFrame,
    index: VectorIndex | None = None,
    top_k: int = 10,
    keyword_weight: float = 0.3,
    semantic_weight: float = 0.7,
) -> list[dict]:
    """Combine keyword + semantic search results."""
    # Keyword results
    kw_results = keyword_search(query, posts_df, top_k=top_k * 2)

    # Semantic results
    sem_results = []
    if index is not None:
        sem_results = semantic_search(query, index, top_k=top_k * 2)

    # Merge and re-rank
    scored = {}
    for r in kw_results:
        key = r["post_id"]
        scored[key] = {
            **r,
            "final_score": r["score"] * keyword_weight,
            "sources": ["keyword"],
        }

    for r in sem_results:
        key = r.get("post_id", r.get("chunk_id", ""))
        if key in scored:
            scored[key]["final_score"] += r["score"] * semantic_weight
            scored[key]["sources"].append("semantic")
        else:
            scored[key] = {
                **r,
                "final_score": r["score"] * semantic_weight,
                "sources": ["semantic"],
            }

    # Sort by final score
    merged = sorted(scored.values(), key=lambda x: x["final_score"], reverse=True)
    return merged[:top_k]


def format_search_result(result: dict) -> dict:
    """Format a search result for display, ensuring source traceability."""
    text = result.get("text", "")
    # Truncate for excerpt
    excerpt = text[:300] + "..." if len(text) > 300 else text

    return {
        "post_id": result.get("post_id", ""),
        "thread_id": result.get("thread_id", ""),
        "comment_id": result.get("comment_id"),
        "excerpt": excerpt,
        "score": result.get("final_score", result.get("score", 0)),
        "sources": result.get("sources", [result.get("source", "unknown")]),
    }

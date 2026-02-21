"""Tests for search: chunking, embedding, indexing, retrieval."""

import pandas as pd
import pytest

from pt_insights_os.search.chunking import chunk_text, prepare_chunks
from pt_insights_os.search.embed import embed_texts, get_backend
from pt_insights_os.search.index import VectorIndex
from pt_insights_os.search.retrieve import (
    format_search_result,
    hybrid_search,
    keyword_search,
)


class TestChunking:
    def test_short_text_single_chunk(self):
        chunks = chunk_text("This is a short text.")
        assert len(chunks) == 1
        assert chunks[0] == "This is a short text."

    def test_empty_text(self):
        chunks = chunk_text("")
        assert len(chunks) == 0

    def test_long_text_splits(self):
        text = ". ".join([f"Sentence number {i}" for i in range(100)])
        chunks = chunk_text(text, max_chunk_size=200)
        assert len(chunks) > 1

    def test_prepare_chunks_from_posts(self):
        posts = [
            {"post_id": "p1", "thread_id": "t1", "text_redacted": "Short post about PT."},
            {"post_id": "p2", "thread_id": "t1", "text_redacted": "Another post about therapy."},
        ]
        chunks = prepare_chunks(posts)
        assert len(chunks) == 2
        assert all("chunk_id" in c for c in chunks)
        assert all("post_id" in c for c in chunks)
        assert all("text" in c for c in chunks)


class TestEmbedding:
    def test_embed_texts(self):
        texts = ["physical therapy practice", "insurance reimbursement"]
        embeddings = embed_texts(texts)
        assert embeddings.shape[0] == 2
        assert embeddings.shape[1] > 0

    def test_backend_detected(self):
        backend = get_backend()
        assert backend in ("sentence_transformers", "tfidf")


class TestVectorIndex:
    @pytest.fixture
    def sample_chunks(self):
        return [
            {
                "chunk_id": "c1",
                "post_id": "p1",
                "thread_id": "t1",
                "text": "Cash-based physical therapy practice transition",
            },
            {
                "chunk_id": "c2",
                "post_id": "p2",
                "thread_id": "t1",
                "text": "Insurance reimbursement rates for outpatient PT",
            },
            {
                "chunk_id": "c3",
                "post_id": "p3",
                "thread_id": "t2",
                "text": "Burnout from high patient volume and documentation burden",
            },
            {
                "chunk_id": "c4",
                "post_id": "p4",
                "thread_id": "t2",
                "text": "Hiring staff PTs and salary benchmarks",
            },
            {
                "chunk_id": "c5",
                "post_id": "p5",
                "thread_id": "t3",
                "text": "WebPT EMR system review and comparison",
            },
        ]

    def test_build_index(self, sample_chunks):
        index = VectorIndex()
        index.build(sample_chunks)
        assert index.embeddings is not None
        assert len(index.chunks) == 5

    def test_search_returns_results(self, sample_chunks):
        index = VectorIndex()
        index.build(sample_chunks)
        results = index.search("cash pay PT clinic", top_k=3)
        assert len(results) > 0
        assert all("score" in r for r in results)

    def test_search_relevance(self, sample_chunks):
        index = VectorIndex()
        index.build(sample_chunks)

        # Search for burnout — should rank burnout chunk highest
        results = index.search("burnout exhaustion", top_k=5)
        assert len(results) > 0
        # The burnout chunk should be in top results
        top_post_ids = [r.get("post_id") for r in results[:3]]
        assert "p3" in top_post_ids

    def test_save_load(self, sample_chunks, tmp_path):
        index = VectorIndex()
        index.build(sample_chunks)
        index.save(tmp_path)

        # Load into new index
        index2 = VectorIndex()
        assert index2.load(tmp_path)
        assert len(index2.chunks) == 5

        # Search should still work
        results = index2.search("EMR system", top_k=3)
        assert len(results) > 0


class TestKeywordSearch:
    def test_keyword_search(self):
        posts_df = pd.DataFrame(
            {
                "post_id": ["p1", "p2", "p3"],
                "thread_id": ["t1", "t1", "t2"],
                "text_redacted": [
                    "Cash-based PT practice is growing",
                    "Insurance reimbursement is declining",
                    "Burnout from documentation burden",
                ],
            }
        )
        results = keyword_search("cash based practice", posts_df)
        assert len(results) > 0
        assert results[0]["post_id"] == "p1"

    def test_keyword_search_no_results(self):
        posts_df = pd.DataFrame(
            {
                "post_id": ["p1"],
                "thread_id": ["t1"],
                "text_redacted": ["Physical therapy discussion"],
            }
        )
        results = keyword_search("xyz789", posts_df)
        assert len(results) == 0


class TestHybridSearch:
    def test_hybrid_search(self):
        posts_df = pd.DataFrame(
            {
                "post_id": ["p1", "p2"],
                "thread_id": ["t1", "t2"],
                "text_redacted": [
                    "Cash-based physical therapy transition",
                    "Burnout from patient overload",
                ],
            }
        )
        # Without semantic (no index)
        results = hybrid_search("cash based therapy", posts_df, index=None)
        assert len(results) > 0


class TestSearchResultFormat:
    def test_format_result(self):
        result = {
            "post_id": "p1",
            "thread_id": "t1",
            "comment_id": None,
            "text": "This is a test result about PT.",
            "score": 0.85,
            "sources": ["keyword", "semantic"],
        }
        formatted = format_search_result(result)
        assert "post_id" in formatted
        assert "thread_id" in formatted
        assert "excerpt" in formatted
        assert formatted["score"] == 0.85

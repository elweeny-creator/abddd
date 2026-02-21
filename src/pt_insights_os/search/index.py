"""Vector index — FAISS if available, else DuckDB cosine similarity."""

import json
import pickle
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np

from pt_insights_os.config import VECTOR_BACKEND, PROJECT_ROOT
from pt_insights_os.logging_config import setup_logging
from pt_insights_os.search.embed import embed_texts, get_backend as get_embed_backend

logger = setup_logging()

INDEX_DIR = PROJECT_ROOT / "data" / "warehouse"


def _detect_vector_backend() -> str:
    if VECTOR_BACKEND != "auto":
        return VECTOR_BACKEND
    try:
        import faiss
        return "faiss"
    except ImportError:
        return "numpy"


class VectorIndex:
    """Unified vector index interface."""

    def __init__(self):
        self.backend = _detect_vector_backend()
        self.chunks: list[dict] = []
        self.embeddings: np.ndarray | None = None
        self._faiss_index = None

    def build(self, chunks: list[dict]) -> None:
        """Build index from chunks (each must have 'text' key)."""
        if not chunks:
            logger.warning("No chunks to index")
            return

        self.chunks = chunks
        texts = [c["text"] for c in chunks]
        self.embeddings = embed_texts(texts)
        dim = self.embeddings.shape[1]

        if self.backend == "faiss":
            import faiss
            self._faiss_index = faiss.IndexFlatIP(dim)  # Inner product (cosine with normalized)
            # Normalize for cosine similarity
            norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)
            normalized = self.embeddings / norms
            self._faiss_index.add(normalized)
            logger.info(f"Built FAISS index: {len(chunks)} chunks, dim={dim}")
        else:
            # numpy cosine — just keep embeddings normalized
            norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)
            self.embeddings = self.embeddings / norms
            logger.info(f"Built numpy cosine index: {len(chunks)} chunks, dim={dim}")

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """Search the index. Returns list of {chunk, score, ...metadata}."""
        if self.embeddings is None or len(self.chunks) == 0:
            return []

        query_vec = embed_texts([query])
        query_norm = np.linalg.norm(query_vec, axis=1, keepdims=True)
        query_norm = np.where(query_norm == 0, 1, query_norm)
        query_vec = query_vec / query_norm

        if self.backend == "faiss":
            scores, indices = self._faiss_index.search(query_vec, min(top_k, len(self.chunks)))
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0:
                    result = {**self.chunks[idx], "score": float(score)}
                    results.append(result)
            return results
        else:
            # Numpy cosine similarity
            similarities = np.dot(self.embeddings, query_vec.T).flatten()
            top_indices = np.argsort(similarities)[::-1][:top_k]
            results = []
            for idx in top_indices:
                if similarities[idx] >= -1:  # Include all; rank handles relevance
                    result = {**self.chunks[idx], "score": float(similarities[idx])}
                    results.append(result)
            return results

    def save(self, path: Path | None = None) -> Path:
        """Save index to disk."""
        save_dir = path or INDEX_DIR
        save_dir.mkdir(parents=True, exist_ok=True)

        index_path = save_dir / "search_index.pkl"
        data = {
            "chunks": self.chunks,
            "embeddings": self.embeddings,
            "backend": self.backend,
        }

        if self.backend == "faiss" and self._faiss_index is not None:
            import faiss
            faiss_path = save_dir / "search_index.faiss"
            faiss.write_index(self._faiss_index, str(faiss_path))
            data["faiss_path"] = str(faiss_path)

        with open(index_path, "wb") as f:
            pickle.dump(data, f)

        logger.info(f"Saved index to {index_path}")
        return index_path

    def load(self, path: Path | None = None) -> bool:
        """Load index from disk. Returns True if successful."""
        load_dir = path or INDEX_DIR
        index_path = load_dir / "search_index.pkl"

        if not index_path.exists():
            return False

        with open(index_path, "rb") as f:
            data = pickle.load(f)

        self.chunks = data["chunks"]
        self.embeddings = data["embeddings"]
        self.backend = data.get("backend", "numpy")

        if self.backend == "faiss" and "faiss_path" in data:
            try:
                import faiss
                self._faiss_index = faiss.read_index(data["faiss_path"])
            except (ImportError, Exception):
                # Fallback to numpy
                self.backend = "numpy"

        logger.info(f"Loaded index: {len(self.chunks)} chunks")
        return True


def save_index_meta(conn, index: VectorIndex) -> None:
    """Save index metadata to DuckDB."""
    meta = {
        "index_id": f"idx_{uuid.uuid4().hex[:12]}",
        "model_name": get_embed_backend(),
        "backend": index.backend,
        "chunk_count": len(index.chunks),
        "created_at": datetime.now(),
        "index_path": str(INDEX_DIR / "search_index.pkl"),
    }
    conn.execute("DELETE FROM embeddings_index_meta")
    conn.execute(
        "INSERT INTO embeddings_index_meta VALUES (?, ?, ?, ?, ?, ?)",
        list(meta.values()),
    )

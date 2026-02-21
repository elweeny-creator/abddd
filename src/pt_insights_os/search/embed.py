"""Embedding layer — sentence-transformers if available, else TF-IDF."""

import numpy as np

from pt_insights_os.config import EMBEDDING_BACKEND, EMBEDDING_MODEL
from pt_insights_os.logging_config import setup_logging

logger = setup_logging()

_embedder = None
_backend = None


def _detect_backend() -> str:
    """Auto-detect best available embedding backend."""
    if EMBEDDING_BACKEND != "auto":
        return EMBEDDING_BACKEND

    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401

        return "sentence_transformers"
    except ImportError:
        pass

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: F401

        return "tfidf"
    except ImportError:
        pass

    raise RuntimeError(
        "No embedding backend available. Install sentence-transformers or scikit-learn."
    )


def _get_st_embedder():
    """Get sentence-transformers embedder."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer(EMBEDDING_MODEL)
        logger.info(f"Loaded sentence-transformers model: {EMBEDDING_MODEL}")
    return _embedder


class TfidfEmbedder:
    """TF-IDF based embedder as fallback."""

    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer

        # Use sublinear_tf and no stop_words to keep vocabulary broad for small corpora
        self.vectorizer = TfidfVectorizer(max_features=384, sublinear_tf=True, ngram_range=(1, 2))
        self._fitted = False

    def fit(self, texts: list[str]):
        self.vectorizer.fit(texts)
        self._fitted = True

    def encode(self, texts: list[str]) -> np.ndarray:
        if not self._fitted:
            self.fit(texts)
        return self.vectorizer.transform(texts).toarray().astype(np.float32)


_tfidf_embedder = None


def get_backend() -> str:
    global _backend
    if _backend is None:
        _backend = _detect_backend()
        logger.info(f"Using embedding backend: {_backend}")
    return _backend


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a list of texts. Returns (n_texts, dim) float32 array."""
    global _tfidf_embedder
    backend = get_backend()

    if backend == "sentence_transformers":
        model = _get_st_embedder()
        embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return embeddings.astype(np.float32)
    else:
        if _tfidf_embedder is None:
            _tfidf_embedder = TfidfEmbedder()
        return _tfidf_embedder.encode(texts)


def embedding_dim() -> int:
    """Get the embedding dimension."""
    backend = get_backend()
    if backend == "sentence_transformers":
        model = _get_st_embedder()
        return model.get_sentence_embedding_dimension()
    else:
        return 384

"""Pure-function embedding helpers — shared between harness and app layers.

The two functions in this module (`cosine_similarity` and `generate_embedding`)
have no FastAPI / chromadb / sentence_transformers dependencies at the
import level. They lazy-load the model on first use.

`app.gateway.embedding_service` re-imports these so its public surface
doesn't change, and `deerflow.knowledge.service` can call them without
crossing the harness → app boundary.
"""
from __future__ import annotations

import hashlib
import logging
import threading

logger = logging.getLogger(__name__)

_model: object | None = None
_model_lock = threading.Lock()
# Sentinel to remember we've already tried and failed.
_MODEL_FAILED: object = object()


def _get_embedding_model():
    """Lazy-load sentence-transformers; returns None on failure."""
    global _model
    if _model is not None:
        return _model if _model is not _MODEL_FAILED else None
    with _model_lock:
        if _model is not None:
            return _model if _model is not _MODEL_FAILED else None
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

            _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            logger.info("Embedding model loaded: all-MiniLM-L6-v2")
            return _model
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to load embedding model: {e}")
            _model = _MODEL_FAILED
            return None


def generate_embedding(text: str) -> list[float]:
    """Return a 384-dim embedding for `text`. Falls back to a hash-derived
    pseudo-vector when the model is unavailable so the rest of the system
    keeps working in degraded mode.
    """
    model = _get_embedding_model()
    if model is not None:
        embedding = model.encode(text)
        return embedding.tolist()
    dim = 384
    text_hash = hashlib.sha256(text.encode()).digest()[:dim]
    return [float(b) / 255.0 * 2.0 - 1.0 for b in text_hash]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Plain cosine similarity — handles zero-norm vectors safely."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

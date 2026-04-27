"""Embedding service for RAG knowledge base using sentence-transformers."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer

    _model: SentenceTransformer | None = None
except ImportError:
    _model = None
    logger.warning("sentence-transformers not installed, using fallback embedding")

try:
    import chromadb
    from chromadb.config import Settings

    _chroma_client: chromadb.ClientAPI | None = None
except ImportError:
    _chroma_client = None
    logger.warning("chromadb not installed, vector operations will be stubbed")


def _get_embedding_model() -> SentenceTransformer | None:
    global _model
    if _model is None and _model is not False:
        try:
            _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            logger.info("Embedding model loaded: all-MiniLM-L6-v2")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            _model = False
    return _model if _model is not False else None


def _get_chroma_client() -> chromadb.ClientAPI | None:
    global _chroma_client
    if _chroma_client is None and _chroma_client is not False:
        try:
            _chroma_client = chromadb.Client(Settings(anonymized_telemetry=False))
            logger.info("ChromaDB client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            _chroma_client = False
    return _chroma_client if _chroma_client is not False else None


def _generate_embedding(text: str) -> list[float]:
    model = _get_embedding_model()
    if model is not None:
        embedding = model.encode(text)
        return embedding.tolist()
    dim = 384
    text_hash = hashlib.sha256(text.encode()).digest()[:dim]
    return [float(b) / 255.0 * 2.0 - 1.0 for b in text_hash]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class EmbeddingService:
    def __init__(self, kb_id: str):
        self.kb_id = kb_id
        self.collection_name = f"kb_{kb_id}"
        self._collection = None
        self._client = _get_chroma_client()

    def _get_or_create_collection(self):
        if self._client is None:
            return None
        try:
            self._collection = self._client.get_or_create_collection(name=self.collection_name, metadata={"kb_id": self.kb_id})
            return self._collection
        except Exception as e:
            logger.error(f"Failed to get/create collection: {e}")
            return None

    def add_chunk(self, chunk_id: str, content: str, metadata: dict[str, Any] | None = None) -> bool:
        collection = self._get_or_create_collection()
        if collection is None:
            return False
        try:
            embedding = _generate_embedding(content)
            collection.add(ids=[chunk_id], embeddings=[embedding], documents=[content], metadatas=[metadata or {}])
            logger.debug(f"Added chunk {chunk_id} to collection {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add chunk: {e}")
            return False

    def search(self, query: str, top_k: int = 5, threshold: float = 0.7) -> list[dict[str, Any]]:
        collection = self._get_or_create_collection()
        if collection is None:
            return []
        try:
            query_embedding = _generate_embedding(query)
            results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
            search_results = []
            if results and results.get("ids") and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    distance = results.get("distances", [[]])[0][i] if results.get("distances") else 0
                    similarity = 1.0 / (1.0 + distance) if distance else 0.85
                    if similarity >= threshold:
                        search_results.append({"id": doc_id, "content": results["documents"][0][i] if results.get("documents") else "", "similarity": similarity, "metadata": results["metadatas"][0][i] if results.get("metadatas") else {}})
            return search_results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def delete_chunk(self, chunk_id: str) -> bool:
        collection = self._get_or_create_collection()
        if collection is None:
            return False
        try:
            collection.delete(ids=[chunk_id])
            return True
        except Exception as e:
            logger.error(f"Failed to delete chunk: {e}")
            return False

    def delete_all(self) -> bool:
        collection = self._get_or_create_collection()
        if collection is None:
            return False
        try:
            collection.delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete all chunks: {e}")
            return False


_embedding_services: dict[str, EmbeddingService] = {}


def get_embedding_service(kb_id: str) -> EmbeddingService:
    if kb_id not in _embedding_services:
        _embedding_services[kb_id] = EmbeddingService(kb_id)
    return _embedding_services[kb_id]

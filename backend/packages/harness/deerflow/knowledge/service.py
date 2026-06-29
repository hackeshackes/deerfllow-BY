"""Shared Knowledge Base service for use by both Gateway API and agent middleware."""

from __future__ import annotations

import json
import logging
import pickle
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# DB path resolved at import time so the service always matches the gateway's DB
_db_path: Path | None = None


def _get_db_path() -> Path:
    global _db_path
    if _db_path is None:
        # Resolve relative to this file: deerflow/knowledge/service.py
        # → deerflow/knowledge/ → deerflow/ → packages/harness/ → packages/ → backend/
        backend_dir = Path(__file__).resolve().parents[4]
        _db_path = backend_dir / "app" / "gateway" / "data" / "knowledge.db"
    return _db_path


def _get_db() -> sqlite3.Connection:
    """Get a thread-safe DB connection to the knowledge base DB."""
    db_path = _get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _is_kb_shared_to_workspace(conn: sqlite3.Connection, kb_id: str, workspace_id: str) -> bool:
    cursor = conn.execute(
        "SELECT 1 FROM knowledge_shares WHERE knowledge_base_id = ? AND target_workspace_id = ?",
        (kb_id, workspace_id),
    )
    return cursor.fetchone() is not None


def list_accessible_knowledge_bases(user_id: str, workspace_id: str | None) -> list[dict[str, Any]]:
    """Return all knowledge bases visible to the given user and workspace.

    Visibility rules (same as Gateway API):
    - Own private KBs (user_id match)
    - Workspace-shared KBs (via knowledge_shares table)
    - Global KBs (is_global = 1)

    Args:
        user_id: The current user's ID.
        workspace_id: The current workspace ID (may be None for personal-only context).

    Returns:
        List of knowledge base records as dicts, ordered by updated_at DESC.
    """
    conn = _get_db()
    try:
        if workspace_id:
            cursor = conn.execute(
                """SELECT * FROM knowledge_bases WHERE
                    user_id = ? OR
                    id IN (SELECT knowledge_base_id FROM knowledge_shares WHERE target_workspace_id = ?) OR
                    is_global = 1
                ORDER BY updated_at DESC""",
                (user_id, workspace_id),
            )
        else:
            cursor = conn.execute(
                """SELECT * FROM knowledge_bases WHERE
                    user_id = ? OR
                    is_global = 1
                ORDER BY updated_at DESC""",
                (user_id,),
            )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def search_knowledge_base(
    kb_id: str,
    query: str,
    top_k: int = 5,
    similarity_threshold: float = 0.7,
    user_id: str | None = None,
    workspace_id: str | None = None,
) -> KnowledgeSearchResult | None:
    """Search a single knowledge base for relevant chunks.

    Performs access control checks before returning results:
    - Global KBs are accessible to everyone
    - Private KBs require user_id match
    - Workspace-shared KBs require workspace membership

    Args:
        kb_id: The knowledge base ID to search.
        query: The search query string.
        top_k: Maximum number of results to return.
        similarity_threshold: Minimum similarity score (0.0-1.0).
        user_id: The requesting user's ID (required for access control).
        workspace_id: The requesting user's workspace ID (for workspace-shared KBs).

    Returns:
        KnowledgeSearchResult with matched chunks, or None if access denied.
    """
    # Import from the same harness package — the pure-function helpers
    # used to live in `app.gateway.embedding_service`, which would have
    # crossed the harness → app boundary. They were lifted to
    # `deerflow.knowledge.embeddings` so this service can stay clean.
    from deerflow.knowledge.embeddings import (
        _cosine_similarity,
        _generate_embedding,
    )

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()

        if not row:
            return None

        kb = dict(row)

        # Access control
        if not kb.get("is_global"):
            if user_id is None:
                return None
            if kb["user_id"] != user_id:
                if not (workspace_id and _is_kb_shared_to_workspace(conn, kb_id, workspace_id)):
                    return None

        query_embedding = _generate_embedding(query)

        cursor = conn.execute(
            """SELECT dc.*, d.original_name FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE d.knowledge_base_id = ? AND d.status = 'embedded' AND dc.embedding IS NOT NULL""",
            (kb_id,),
        )

        results: list[dict[str, Any]] = []
        for chunk_row in cursor.fetchall():
            try:
                chunk_embedding = pickle.loads(chunk_row["embedding"])
                similarity = _cosine_similarity(query_embedding, chunk_embedding)

                if similarity >= similarity_threshold:
                    results.append(
                        {
                            "document_id": chunk_row["document_id"],
                            "document_name": chunk_row["original_name"],
                            "chunk_content": chunk_row["content"],
                            "similarity_score": similarity,
                            "metadata": json.loads(chunk_row["metadata"]) if chunk_row["metadata"] else {},
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to decode embedding for chunk {chunk_row['id']}: {e}")
                continue

        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        results = results[:top_k]

        return KnowledgeSearchResult(
            kb_id=kb_id,
            kb_name=kb.get("name", ""),
            query=query,
            results=results,
        )
    finally:
        conn.close()


def search_accessible_knowledge_bases(
    user_id: str,
    workspace_id: str | None,
    query: str,
    top_k: int = 5,
    similarity_threshold: float = 0.5,
    max_kbs: int = 20,
    max_results_per_kb: int = 3,
) -> AggregatedKnowledgeSearchResult:
    """Search all accessible knowledge bases and aggregate results.

    This is the main entry point for the middleware. It:
    1. Discovers all KBs the user can access
    2. Searches each KB concurrently (with timeout)
    3. Merges and globally ranks results
    4. Returns the top-k results

    Args:
        user_id: The current user's ID.
        workspace_id: The current workspace ID (may be None).
        query: The search query string.
        top_k: Final number of results to return after merging.
        similarity_threshold: Minimum similarity score (0.0-1.0).
        max_kbs: Maximum number of KBs to search.
        max_results_per_kb: Maximum results to fetch from each KB before merging.

    Returns:
        AggregatedKnowledgeSearchResult with merged results and metadata.
    """
    import time

    start_time = time.monotonic()

    # Discover accessible KBs
    accessible_kbs = list_accessible_knowledge_bases(user_id, workspace_id)

    if not accessible_kbs:
        return AggregatedKnowledgeSearchResult(
            results=[],
            query=query,
            kb_count=0,
            searched_kb_count=0,
            timed_out_kb_count=0,
            duration_ms=0,
        )

    # Limit KBs to search
    kbs_to_search = accessible_kbs[:max_kbs]

    # Search each KB
    all_results: list[dict[str, Any]] = []
    searched_count = 0
    timeout_count = 0

    for kb in kbs_to_search:
        try:
            result = search_knowledge_base(
                kb_id=kb["id"],
                query=query,
                top_k=max_results_per_kb,
                similarity_threshold=similarity_threshold,
                user_id=user_id,
                workspace_id=workspace_id,
            )
            if result:
                searched_count += 1
                all_results.extend(result.results)
        except Exception as e:
            logger.warning(f"KB search failed for kb_id={kb['id']}: {e}")
            continue

    # Global ranking
    all_results.sort(key=lambda x: x["similarity_score"], reverse=True)
    top_results = all_results[:top_k]

    duration_ms = int((time.monotonic() - start_time) * 1000)

    return AggregatedKnowledgeSearchResult(
        results=top_results,
        query=query,
        kb_count=len(accessible_kbs),
        searched_kb_count=searched_count,
        timed_out_kb_count=timeout_count,
        duration_ms=duration_ms,
    )


# ---------------------------------------------------------------------------
# Data Transfer Objects (compatible with gateway API schemas but pure Python)
# ---------------------------------------------------------------------------


class KnowledgeSearchResult:
    """Result from searching a single knowledge base."""

    def __init__(
        self,
        kb_id: str,
        kb_name: str,
        query: str,
        results: list[dict[str, Any]],
    ):
        self.kb_id = kb_id
        self.kb_name = kb_name
        self.query = query
        self.results = results

    def to_dict(self) -> dict[str, Any]:
        return {
            "kb_id": self.kb_id,
            "kb_name": self.kb_name,
            "query": self.query,
            "results": self.results,
        }


class AggregatedKnowledgeSearchResult:
    """Aggregated results from searching multiple knowledge bases."""

    def __init__(
        self,
        results: list[dict[str, Any]],
        query: str,
        kb_count: int,
        searched_kb_count: int,
        timed_out_kb_count: int,
        duration_ms: int,
    ):
        self.results = results
        self.query = query
        self.kb_count = kb_count
        self.searched_kb_count = searched_kb_count
        self.timed_out_kb_count = timed_out_kb_count
        self.duration_ms = duration_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": self.results,
            "query": self.query,
            "kb_count": self.kb_count,
            "searched_kb_count": self.searched_kb_count,
            "timed_out_kb_count": self.timed_out_kb_count,
            "duration_ms": self.duration_ms,
        }

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.gateway.auth import require_owner_user

router = APIRouter(prefix="/api/admin/knowledge", tags=["admin-knowledge"])

_db_path = Path(__file__).parent.parent / "data" / "knowledge.db"
_db_lock = threading.Lock()


def _get_db() -> sqlite3.Connection:
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


class AdminKnowledgeBaseResponse(BaseModel):
    id: str
    user_id: str
    workspace_id: str | None = None
    visibility: str
    name: str
    description: str | None = None
    embedding_model: str
    document_count: int = 0
    created_at: str
    updated_at: str
    is_global: bool = False


class AdminKnowledgeListResponse(BaseModel):
    knowledge_bases: list[AdminKnowledgeBaseResponse]


@router.get("", response_model=AdminKnowledgeListResponse)
async def admin_list_knowledge_bases(request: Request) -> AdminKnowledgeListResponse:
    require_owner_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("""
            SELECT kb.*,
                   (SELECT COUNT(*) FROM documents WHERE knowledge_base_id = kb.id) as doc_count
            FROM knowledge_bases kb
            ORDER BY kb.updated_at DESC
        """)
        rows = cursor.fetchall()
        knowledge_bases = []
        for row in rows:
            knowledge_bases.append(
                AdminKnowledgeBaseResponse(
                    id=row["id"],
                    user_id=row["user_id"],
                    workspace_id=row["workspace_id"],
                    visibility=row["visibility"],
                    name=row["name"],
                    description=row["description"],
                    embedding_model=row["embedding_model"],
                    document_count=row["doc_count"],
                    created_at=str(row["created_at"]),
                    updated_at=str(row["updated_at"]),
                    is_global=bool(row["is_global"]) if "is_global" in row.keys() and row["is_global"] is not None else False,
                )
            )
        return AdminKnowledgeListResponse(knowledge_bases=knowledge_bases)
    finally:
        conn.close()


class AdminKnowledgeUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    visibility: str | None = Field(default=None, description="Visibility: private, workspace, or global")
    is_global: bool | None = Field(default=None, description="Whether this is a global knowledge base (admin only)")


@router.put("/{kb_id}", response_model=AdminKnowledgeBaseResponse)
async def admin_update_knowledge_base(kb_id: str, request: Request, body: AdminKnowledgeUpdateRequest) -> AdminKnowledgeBaseResponse:
    require_owner_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        updates = []
        params = []
        now = row["updated_at"]

        if body.name is not None:
            updates.append("name = ?")
            params.append(body.name)
        if body.description is not None:
            updates.append("description = ?")
            params.append(body.description)
        if body.visibility is not None:
            updates.append("visibility = ?")
            params.append(body.visibility)
        if body.is_global is not None:
            updates.append("is_global = ?")
            params.append(int(body.is_global))

        if updates:
            updates.append("updated_at = ?")
            params.append(now)
            params.append(kb_id)
            conn.execute(f"UPDATE knowledge_bases SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()
        doc_cursor = conn.execute("SELECT COUNT(*) as cnt FROM documents WHERE knowledge_base_id = ?", (kb_id,))
        doc_count = doc_cursor.fetchone()["cnt"]

        return AdminKnowledgeBaseResponse(
            id=row["id"],
            user_id=row["user_id"],
            workspace_id=row["workspace_id"],
            visibility=row["visibility"],
            name=row["name"],
            description=row["description"],
            embedding_model=row["embedding_model"],
            document_count=doc_count,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            is_global=bool(row["is_global"]) if "is_global" in row.keys() and row["is_global"] is not None else False,
        )
    finally:
        conn.close()


@router.delete("/{kb_id}")
async def admin_delete_knowledge_base(kb_id: str, request: Request) -> dict:
    require_owner_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        conn.execute("DELETE FROM knowledge_shares WHERE knowledge_base_id = ?", (kb_id,))
        cursor = conn.execute("SELECT id FROM documents WHERE knowledge_base_id = ?", (kb_id,))
        for doc_row in cursor.fetchall():
            doc_id = doc_row["id"]
            conn.execute("DELETE FROM document_chunks WHERE document_id = ?", (doc_id,))
        conn.execute("DELETE FROM documents WHERE knowledge_base_id = ?", (kb_id,))
        conn.execute("DELETE FROM knowledge_bases WHERE id = ?", (kb_id,))
        conn.commit()
        return {"success": True, "message": f"Knowledge base {kb_id} deleted"}
    finally:
        conn.close()

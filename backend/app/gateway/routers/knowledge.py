"""Knowledge Base API - RAG knowledge management with SQLite persistence."""

from __future__ import annotations

import json
import logging
import pickle
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from app.gateway.auth import require_user
from app.gateway.auth_context import get_current_workspace_id
from app.gateway.services.document_processor import process_document
from app.gateway.services.embedding_service import _cosine_similarity, _generate_embedding

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

_db_path = Path(__file__).parent.parent / "data" / "knowledge.db"
_db_lock = threading.Lock()


def _get_db() -> sqlite3.Connection:
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _db_lock:
        conn = _get_db()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                workspace_id TEXT,
                visibility TEXT DEFAULT 'private',
                name TEXT NOT NULL,
                description TEXT,
                embedding_model TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                knowledge_base_id TEXT NOT NULL,
                original_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                storage_path TEXT,
                status TEXT NOT NULL,
                chunk_count INTEGER DEFAULT 0,
                token_count INTEGER DEFAULT 0,
                uploaded_at REAL NOT NULL,
                processed_at REAL,
                FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS document_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding BLOB,
                metadata TEXT DEFAULT '{}',
                chunk_index INTEGER DEFAULT 0,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS knowledge_shares (
                id TEXT PRIMARY KEY,
                knowledge_base_id TEXT NOT NULL,
                target_workspace_id TEXT NOT NULL,
                permission TEXT DEFAULT 'read',
                shared_by TEXT NOT NULL,
                shared_at REAL NOT NULL,
                FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE,
                UNIQUE(knowledge_base_id, target_workspace_id)
            );
            CREATE INDEX IF NOT EXISTS idx_kb_user_id ON knowledge_bases(user_id);
            CREATE INDEX IF NOT EXISTS idx_documents_kb_id ON documents(knowledge_base_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
            CREATE INDEX IF NOT EXISTS idx_kb_shares_kb_id ON knowledge_shares(knowledge_base_id);
        """)
        conn.commit()

        # Migration: add is_global column if not exists
        cursor = conn.execute("PRAGMA table_info(knowledge_bases)")
        columns = [row[1] for row in cursor.fetchall()]
        if "is_global" not in columns:
            conn.execute("ALTER TABLE knowledge_bases ADD COLUMN is_global BOOLEAN DEFAULT FALSE")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kb_is_global ON knowledge_bases(is_global)")
            conn.commit()

        conn.close()


_init_db()


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    is_global: bool = Field(default=False, description="Admin only: create as global knowledge base")
    visibility: str = Field(default="private", description="Visibility: private, workspace, or global")


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class KnowledgeBaseResponse(BaseModel):
    id: str
    user_id: str
    workspace_id: str | None = None
    visibility: str = "private"
    name: str
    description: str | None = None
    embedding_model: str
    document_count: int = 0
    created_at: str
    updated_at: str
    shared_to: list[str] = []
    is_global: bool = False


class KnowledgeShareRequest(BaseModel):
    target_workspace_id: str
    permission: str = "read"


class ShareResponse(BaseModel):
    id: str
    knowledge_base_id: str
    target_workspace_id: str
    permission: str
    shared_by: str
    shared_at: str


class DocumentResponse(BaseModel):
    id: str
    knowledge_base_id: str
    original_name: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int = 0
    token_count: int = 0
    uploaded_at: str
    processed_at: str | None = None


class TextDocumentRequest(BaseModel):
    content: str = Field(min_length=1, description="Text content to save")
    title: str | None = Field(default=None, description="Optional title for the document")


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class SearchResult(BaseModel):
    document_id: str
    document_name: str
    chunk_content: str
    similarity_score: float
    metadata: dict[str, Any] = {}


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
    knowledge_base_id: str


def _get_kb_shares(kb_id: str) -> list[str]:
    conn = _get_db()
    try:
        cursor = conn.execute(
            "SELECT target_workspace_id FROM knowledge_shares WHERE knowledge_base_id = ?",
            (kb_id,),
        )
        return [row["target_workspace_id"] for row in cursor.fetchall()]
    finally:
        conn.close()


def _is_kb_shared_to_workspace(kb_id: str, workspace_id: str) -> bool:
    conn = _get_db()
    try:
        cursor = conn.execute(
            "SELECT 1 FROM knowledge_shares WHERE knowledge_base_id = ? AND target_workspace_id = ?",
            (kb_id, workspace_id),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def _kb_response_from_row(row: sqlite3.Row, conn: sqlite3.Connection) -> KnowledgeBaseResponse:
    kb_id = row["id"]
    cursor = conn.execute("SELECT COUNT(*) as cnt FROM documents WHERE knowledge_base_id = ?", (kb_id,))
    doc_count = cursor.fetchone()["cnt"]

    return KnowledgeBaseResponse(
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
        shared_to=_get_kb_shares(kb_id),
        is_global=bool(row["is_global"]) if "is_global" in row.keys() and row["is_global"] is not None else False,
    )


@router.post("", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(body: KnowledgeBaseCreate, request: Request) -> KnowledgeBaseResponse:
    user = require_user(request)
    workspace_id = get_current_workspace_id()

    kb_id = str(uuid.uuid4())
    now = time.time()

    is_global = bool(body.is_global) and user.is_owner
    visibility = body.visibility if body.visibility in ("private", "workspace", "global") else "private"
    if visibility == "global" and not user.is_owner:
        visibility = "private"

    conn = _get_db()
    try:
        conn.execute(
            """INSERT INTO knowledge_bases
                (id, user_id, workspace_id, visibility, name, description, embedding_model, created_at, updated_at, is_global)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                kb_id,
                user.id,
                workspace_id,
                visibility,
                body.name,
                body.description,
                body.embedding_model,
                now,
                now,
                is_global,
            ),
        )
        conn.commit()

        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()
        logger.info(f"Knowledge base created: {kb_id} by user {user.id} in workspace {workspace_id}, is_global={is_global}")
        return _kb_response_from_row(row, conn)
    finally:
        conn.close()


@router.get("", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(request: Request) -> list[KnowledgeBaseResponse]:
    user = require_user(request)
    workspace_id = get_current_workspace_id()

    conn = _get_db()
    try:
        cursor = conn.execute(
            """SELECT * FROM knowledge_bases WHERE
                user_id = ? OR
                id IN (SELECT knowledge_base_id FROM knowledge_shares WHERE target_workspace_id = ?) OR
                is_global = 1
            ORDER BY updated_at DESC""",
            (user.id, workspace_id),
        )
        rows = cursor.fetchall()
        return [_kb_response_from_row(row, conn) for row in rows]
    finally:
        conn.close()


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(kb_id: str, request: Request) -> KnowledgeBaseResponse:
    user = require_user(request)
    workspace_id = get_current_workspace_id()

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        kb = dict(row)
        if kb["is_global"]:
            return _kb_response_from_row(row, conn)
        if kb["user_id"] != user.id:
            if not (workspace_id and _is_kb_shared_to_workspace(kb_id, workspace_id)):
                raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        return _kb_response_from_row(row, conn)
    finally:
        conn.close()


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(kb_id: str, body: KnowledgeBaseUpdate, request: Request) -> KnowledgeBaseResponse:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        kb = dict(row)
        if kb.get("is_global"):
            if not user.is_owner:
                raise HTTPException(status_code=403, detail="Only admin can update global knowledge base")
        elif row["user_id"] != user.id:
            raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        now = time.time()
        updates = []
        params = []

        if body.name is not None:
            updates.append("name = ?")
            params.append(body.name)
        if body.description is not None:
            updates.append("description = ?")
            params.append(body.description)

        updates.append("updated_at = ?")
        params.append(now)
        params.append(kb_id)

        conn.execute(f"UPDATE knowledge_bases SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()
        return _kb_response_from_row(row, conn)
    finally:
        conn.close()


@router.delete("/{kb_id}")
async def delete_knowledge_base(kb_id: str, request: Request) -> dict:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        if row["user_id"] != user.id and not user.is_owner:
            raise HTTPException(status_code=403, detail="Only the owner or admin can delete this knowledge base")

        conn.execute("DELETE FROM knowledge_shares WHERE knowledge_base_id = ?", (kb_id,))
        cursor = conn.execute("SELECT id FROM documents WHERE knowledge_base_id = ?", (kb_id,))
        for doc_row in cursor.fetchall():
            doc_id = doc_row["id"]
            conn.execute("DELETE FROM document_chunks WHERE document_id = ?", (doc_id,))
        conn.execute("DELETE FROM documents WHERE knowledge_base_id = ?", (kb_id,))
        conn.execute("DELETE FROM knowledge_bases WHERE id = ?", (kb_id,))
        conn.commit()

        logger.info(f"Knowledge base deleted: {kb_id}")
        return {"success": True, "message": f"Knowledge base {kb_id} deleted"}
    finally:
        conn.close()


@router.post("/{kb_id}/documents", response_model=DocumentResponse)
async def upload_document(kb_id: str, request: Request, file: UploadFile = File(...)) -> DocumentResponse:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        kb = dict(row)
        if kb["is_global"]:
            if not user.is_owner:
                raise HTTPException(status_code=403, detail="Only admin can upload documents to global knowledge base")
        elif kb["user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Only the owner can upload documents")

        doc_id = str(uuid.uuid4())
        now = time.time()

        file_type = file.filename.split(".")[-1].lower() if file.filename else "unknown"
        allowed_types = ["pdf", "docx", "txt", "md", "csv"]
        if file_type not in allowed_types:
            raise HTTPException(status_code=422, detail=f"File type {file_type} not supported. Allowed: {allowed_types}")

        content = await file.read()
        file_size = len(content)

        storage_path = f"/mnt/user-data/knowledge/{kb_id}/{doc_id}/{file.filename}"
        conn.execute(
            """INSERT INTO documents
                (id, knowledge_base_id, original_name, file_type, file_size, storage_path, status, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                doc_id,
                kb_id,
                file.filename or "unknown",
                file_type,
                file_size,
                storage_path,
                "processing",
                now,
            ),
        )
        conn.commit()

        chunks = await process_document(storage_path, file_type)
        chunk_count = len(chunks)
        total_tokens = sum(len(c["content"]) // 4 for c in chunks)

        for idx, chunk in enumerate(chunks):
            embedding = _generate_embedding(chunk["content"])
            embedding_blob = pickle.dumps(embedding)
            metadata_json = json.dumps(chunk.get("metadata", {}))
            conn.execute(
                """INSERT INTO document_chunks
                    (id, document_id, content, embedding, metadata, chunk_index)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    doc_id,
                    chunk["content"],
                    embedding_blob,
                    metadata_json,
                    idx,
                ),
            )

        conn.execute(
            "UPDATE documents SET status = ?, chunk_count = ?, token_count = ?, processed_at = ? WHERE id = ?",
            ("embedded", chunk_count, total_tokens, now, doc_id),
        )
        conn.commit()

        logger.info(f"Document uploaded and processed: {doc_id} to knowledge base {kb_id}, {chunk_count} chunks")
        return DocumentResponse(
            id=doc_id,
            knowledge_base_id=kb_id,
            original_name=file.filename or "unknown",
            file_type=file_type,
            file_size=file_size,
            status="embedded",
            chunk_count=chunk_count,
            token_count=total_tokens,
            uploaded_at=str(now),
            processed_at=str(now),
        )
    finally:
        conn.close()


@router.post("/{kb_id}/text", response_model=DocumentResponse)
async def add_text_document(kb_id: str, body: TextDocumentRequest, request: Request) -> DocumentResponse:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        kb = dict(row)
        if kb.get("is_global"):
            if not user.is_owner:
                raise HTTPException(status_code=403, detail="Only admin can add documents to global knowledge base")
        elif kb["user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Only the owner can add documents")

        doc_id = str(uuid.uuid4())
        now = time.time()
        title = body.title or "Captured Summary"
        content = body.content
        file_size = len(content.encode("utf-8"))

        conn.execute(
            """INSERT INTO documents
                (id, knowledge_base_id, original_name, file_type, file_size, storage_path, status, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                doc_id,
                kb_id,
                f"{title}.txt",
                "txt",
                file_size,
                f"/mnt/user-data/knowledge/{kb_id}/{doc_id}/{title}.txt",
                "ready",
                now,
            ),
        )

        embedding = _generate_embedding(content)
        embedding_blob = pickle.dumps(embedding)

        conn.execute(
            """INSERT INTO document_chunks
                (id, document_id, content, embedding, chunk_index)
            VALUES (?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                doc_id,
                content,
                embedding_blob,
                0,
            ),
        )
        conn.commit()

        logger.info(f"Text document added: {doc_id} to knowledge base {kb_id}")
        return DocumentResponse(
            id=doc_id,
            knowledge_base_id=kb_id,
            original_name=f"{title}.txt",
            file_type="txt",
            file_size=file_size,
            status="embedded",
            chunk_count=1,
            token_count=0,
            uploaded_at=str(now),
            processed_at=str(now),
        )
    finally:
        conn.close()


@router.get("/{kb_id}/documents", response_model=list[DocumentResponse])
async def list_documents(kb_id: str, request: Request) -> list[DocumentResponse]:
    user = require_user(request)
    workspace_id = get_current_workspace_id()

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        kb = dict(row)
        if kb.get("is_global"):
            pass
        elif kb["user_id"] != user.id:
            if not (workspace_id and _is_kb_shared_to_workspace(kb_id, workspace_id)):
                raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        cursor = conn.execute(
            "SELECT * FROM documents WHERE knowledge_base_id = ? ORDER BY uploaded_at DESC",
            (kb_id,),
        )
        docs = []
        for doc_row in cursor.fetchall():
            docs.append(
                DocumentResponse(
                    id=doc_row["id"],
                    knowledge_base_id=doc_row["knowledge_base_id"],
                    original_name=doc_row["original_name"],
                    file_type=doc_row["file_type"],
                    file_size=doc_row["file_size"],
                    status=doc_row["status"],
                    chunk_count=doc_row["chunk_count"],
                    token_count=doc_row["token_count"],
                    uploaded_at=str(doc_row["uploaded_at"]),
                    processed_at=str(doc_row["processed_at"]) if doc_row["processed_at"] else None,
                )
            )
        return docs
    finally:
        conn.close()


@router.delete("/{kb_id}/documents/{doc_id}")
async def delete_document(kb_id: str, doc_id: str, request: Request) -> dict:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        kb = dict(row)
        if kb.get("is_global"):
            if not user.is_owner:
                raise HTTPException(status_code=403, detail="Only admin can delete documents from global knowledge base")
        elif row["user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Only the owner can delete documents")

        cursor = conn.execute("SELECT * FROM documents WHERE id = ? AND knowledge_base_id = ?", (doc_id, kb_id))
        doc = cursor.fetchone()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

        conn.execute("DELETE FROM document_chunks WHERE document_id = ?", (doc_id,))
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()

        logger.info(f"Document deleted: {doc_id}")
        return {"success": True, "message": f"Document {doc_id} deleted"}
    finally:
        conn.close()


@router.post("/{kb_id}/documents/{doc_id}/reindex")
async def reindex_document(kb_id: str, doc_id: str, request: Request) -> DocumentResponse:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        kb = dict(row)
        if kb.get("is_global"):
            if not user.is_owner:
                raise HTTPException(status_code=403, detail="Only admin can reindex documents in global knowledge base")
        elif row["user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Only the owner can reindex documents")

        cursor = conn.execute("SELECT * FROM documents WHERE id = ? AND knowledge_base_id = ?", (doc_id, kb_id))
        doc = cursor.fetchone()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

        doc = dict(doc)
        now = time.time()

        cursor = conn.execute("SELECT content FROM document_chunks WHERE document_id = ?", (doc_id,))
        existing_chunks = cursor.fetchall()

        conn.execute("DELETE FROM document_chunks WHERE document_id = ?", (doc_id,))

        if doc["file_type"] == "txt":
            if existing_chunks:
                for idx, chunk_row in enumerate(existing_chunks):
                    embedding = _generate_embedding(chunk_row["content"])
                    embedding_blob = pickle.dumps(embedding)
                    conn.execute(
                        """INSERT INTO document_chunks
                            (id, document_id, content, embedding, chunk_index)
                        VALUES (?, ?, ?, ?, ?)""",
                        (str(uuid.uuid4()), doc_id, chunk_row["content"], embedding_blob, idx),
                    )
            chunk_count = len(existing_chunks) if existing_chunks else 0
            total_tokens = 0
        else:
            chunks = await process_document(doc["storage_path"], doc["file_type"])
            chunk_count = len(chunks)
            for idx, chunk in enumerate(chunks):
                embedding = _generate_embedding(chunk["content"])
                embedding_blob = pickle.dumps(embedding)
                metadata_json = json.dumps(chunk.get("metadata", {}))
                conn.execute(
                    """INSERT INTO document_chunks
                        (id, document_id, content, embedding, metadata, chunk_index)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (str(uuid.uuid4()), doc_id, chunk["content"], embedding_blob, metadata_json, idx),
                )
            total_tokens = sum(len(c["content"]) // 4 for c in chunks)
        conn.execute(
            "UPDATE documents SET status = ?, chunk_count = ?, token_count = ?, processed_at = ? WHERE id = ?",
            ("embedded", chunk_count, total_tokens, now, doc_id),
        )
        conn.commit()

        logger.info(f"Document reindexed: {doc_id}, {chunk_count} chunks with real embeddings")
        return DocumentResponse(
            id=doc["id"],
            knowledge_base_id=doc["knowledge_base_id"],
            original_name=doc["original_name"],
            file_type=doc["file_type"],
            file_size=doc["file_size"],
            status="embedded",
            chunk_count=chunk_count,
            token_count=total_tokens,
            uploaded_at=str(doc["uploaded_at"]),
            processed_at=str(now),
        )
    finally:
        conn.close()


@router.post("/{kb_id}/reindex-all")
async def reindex_all_documents(kb_id: str, request: Request) -> dict:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        kb = dict(row)
        if kb.get("is_global"):
            if not user.is_owner:
                raise HTTPException(status_code=403, detail="Only admin can reindex global knowledge base")
        elif row["user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Only the owner can reindex documents")

        cursor = conn.execute("SELECT id FROM documents WHERE knowledge_base_id = ?", (kb_id,))
        doc_ids = [row["id"] for row in cursor.fetchall()]

        reindexed = 0
        for doc_id in doc_ids:
            cursor = conn.execute("SELECT * FROM documents WHERE id = ? AND knowledge_base_id = ?", (doc_id, kb_id))
            doc = cursor.fetchone()
            if not doc:
                continue
            doc = dict(doc)
            now = time.time()

            cursor = conn.execute("SELECT content FROM document_chunks WHERE document_id = ?", (doc_id,))
            existing_chunks = cursor.fetchall()

            conn.execute("DELETE FROM document_chunks WHERE document_id = ?", (doc_id,))

            if doc["file_type"] == "txt":
                if existing_chunks:
                    for idx, chunk_row in enumerate(existing_chunks):
                        embedding = _generate_embedding(chunk_row["content"])
                        embedding_blob = pickle.dumps(embedding)
                        conn.execute(
                            """INSERT INTO document_chunks
                                (id, document_id, content, embedding, chunk_index)
                            VALUES (?, ?, ?, ?, ?)""",
                            (str(uuid.uuid4()), doc_id, chunk_row["content"], embedding_blob, idx),
                        )
                chunk_count = len(existing_chunks) if existing_chunks else 0
                total_tokens = 0
            else:
                chunks = await process_document(doc["storage_path"], doc["file_type"])
                chunk_count = len(chunks)
                for idx, chunk in enumerate(chunks):
                    embedding = _generate_embedding(chunk["content"])
                    embedding_blob = pickle.dumps(embedding)
                    metadata_json = json.dumps(chunk.get("metadata", {}))
                    conn.execute(
                        """INSERT INTO document_chunks
                            (id, document_id, content, embedding, metadata, chunk_index)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                        (str(uuid.uuid4()), doc_id, chunk["content"], embedding_blob, metadata_json, idx),
                    )
                total_tokens = sum(len(c["content"]) // 4 for c in chunks)

            conn.execute(
                "UPDATE documents SET status = ?, chunk_count = ?, token_count = ?, processed_at = ? WHERE id = ?",
                ("embedded", chunk_count, total_tokens, now, doc_id),
            )
            reindexed += 1

        conn.commit()
        logger.info(f"Reindexed {reindexed} documents in knowledge base {kb_id}")
        return {"success": True, "message": f"Reindexed {reindexed} documents"}
    finally:
        conn.close()


@router.post("/{kb_id}/share", response_model=ShareResponse)
async def share_knowledge_base(kb_id: str, body: KnowledgeShareRequest, request: Request) -> ShareResponse:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        kb = dict(row)
        if kb.get("is_global"):
            if not user.is_owner:
                raise HTTPException(status_code=403, detail="Global knowledge bases cannot be shared")
        elif row["user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Only the owner can share this knowledge base")

        cursor = conn.execute(
            "SELECT 1 FROM knowledge_shares WHERE knowledge_base_id = ? AND target_workspace_id = ?",
            (kb_id, body.target_workspace_id),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="Already shared to this workspace")

        share_id = str(uuid.uuid4())
        now = time.time()

        conn.execute(
            """INSERT INTO knowledge_shares
                (id, knowledge_base_id, target_workspace_id, permission, shared_by, shared_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (share_id, kb_id, body.target_workspace_id, body.permission, user.id, now),
        )
        conn.commit()

        logger.info(f"Knowledge base {kb_id} shared to workspace {body.target_workspace_id}")
        return ShareResponse(
            id=share_id,
            knowledge_base_id=kb_id,
            target_workspace_id=body.target_workspace_id,
            permission=body.permission,
            shared_by=user.id,
            shared_at=str(now),
        )
    finally:
        conn.close()


@router.delete("/{kb_id}/share/{share_id}")
async def unshare_knowledge_base(kb_id: str, share_id: str, request: Request) -> dict:
    user = require_user(request)

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        kb = dict(row)
        if kb.get("is_global"):
            if not user.is_owner:
                raise HTTPException(status_code=403, detail="Global knowledge bases cannot be unshared")
        elif row["user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Only the owner can unshare this knowledge base")

        cursor = conn.execute(
            "SELECT * FROM knowledge_shares WHERE id = ? AND knowledge_base_id = ?",
            (share_id, kb_id),
        )
        share = cursor.fetchone()
        if not share:
            raise HTTPException(status_code=404, detail=f"Share {share_id} not found")

        conn.execute("DELETE FROM knowledge_shares WHERE id = ?", (share_id,))
        conn.commit()

        logger.info(f"Knowledge base {kb_id} unshared (share {share_id})")
        return {"success": True, "message": f"Share {share_id} removed"}
    finally:
        conn.close()


@router.post("/{kb_id}/search", response_model=SearchResponse)
async def semantic_search(kb_id: str, body: SearchRequest, request: Request) -> SearchResponse:
    user = require_user(request)
    workspace_id = get_current_workspace_id()

    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        kb = dict(row)
        if kb.get("is_global"):
            pass
        elif kb["user_id"] != user.id:
            if not (workspace_id and _is_kb_shared_to_workspace(kb_id, workspace_id)):
                raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

        query_embedding = _generate_embedding(body.query)

        cursor = conn.execute(
            """SELECT dc.*, d.original_name FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE d.knowledge_base_id = ? AND d.status = 'embedded' AND dc.embedding IS NOT NULL""",
            (kb_id,),
        )

        results = []
        for chunk_row in cursor.fetchall():
            try:
                chunk_embedding = pickle.loads(chunk_row["embedding"])
                similarity = _cosine_similarity(query_embedding, chunk_embedding)

                if similarity >= body.similarity_threshold:
                    results.append(
                        SearchResult(
                            document_id=chunk_row["document_id"],
                            document_name=chunk_row["original_name"],
                            chunk_content=chunk_row["content"],
                            similarity_score=similarity,
                            metadata=json.loads(chunk_row["metadata"]) if chunk_row["metadata"] else {},
                        )
                    )
            except Exception as e:
                logger.warning(f"Failed to decode embedding for chunk {chunk_row['id']}: {e}")
                continue

        results.sort(key=lambda x: x.similarity_score, reverse=True)
        results = results[: body.top_k]

        return SearchResponse(
            results=results,
            query=body.query,
            knowledge_base_id=kb_id,
        )
    finally:
        conn.close()

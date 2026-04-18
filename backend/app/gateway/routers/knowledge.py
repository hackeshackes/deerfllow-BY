"""Knowledge Base API - RAG knowledge management."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from pydantic import BaseModel, Field

from app.gateway.auth import require_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class KnowledgeBaseResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str | None = None
    embedding_model: str
    document_count: int = 0
    created_at: str
    updated_at: str


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


_knowledge_bases: dict[str, dict] = {}
_documents: dict[str, dict] = {}
_document_chunks: dict[str, list[dict]] = {}


def _calculate_embedding(text: str) -> list[float]:
    return [0.0] * 384


def _calculate_similarity(embedding1: list[float], embedding2: list[float]) -> float:
    return 0.85


@router.post("", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(body: KnowledgeBaseCreate, request: Request) -> KnowledgeBaseResponse:
    user = require_user(request)

    kb_id = str(uuid.uuid4())
    now = time.time()

    kb = {
        "id": kb_id,
        "user_id": user.id,
        "name": body.name,
        "description": body.description,
        "embedding_model": body.embedding_model,
        "created_at": now,
        "updated_at": now,
    }
    _knowledge_bases[kb_id] = kb
    logger.info(f"Knowledge base created: {kb_id} by user {user.id}")

    return KnowledgeBaseResponse(
        id=kb["id"],
        user_id=kb["user_id"],
        name=kb["name"],
        description=kb["description"],
        embedding_model=kb["embedding_model"],
        document_count=0,
        created_at=str(kb["created_at"]),
        updated_at=str(kb["updated_at"]),
    )


@router.get("", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(request: Request) -> list[KnowledgeBaseResponse]:
    user = require_user(request)
    result = []
    for kb in _knowledge_bases.values():
        if kb["user_id"] == user.id:
            doc_count = sum(1 for d in _documents.values() if d["knowledge_base_id"] == kb["id"])
            result.append(
                KnowledgeBaseResponse(
                    id=kb["id"],
                    user_id=kb["user_id"],
                    name=kb["name"],
                    description=kb["description"],
                    embedding_model=kb["embedding_model"],
                    document_count=doc_count,
                    created_at=str(kb["created_at"]),
                    updated_at=str(kb["updated_at"]),
                )
            )
    result.sort(key=lambda x: x.updated_at, reverse=True)
    return result


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(kb_id: str, request: Request) -> KnowledgeBaseResponse:
    user = require_user(request)
    kb = _knowledge_bases.get(kb_id)
    if not kb or kb["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

    doc_count = sum(1 for d in _documents.values() if d["knowledge_base_id"] == kb_id)
    return KnowledgeBaseResponse(
        id=kb["id"],
        user_id=kb["user_id"],
        name=kb["name"],
        description=kb["description"],
        embedding_model=kb["embedding_model"],
        document_count=doc_count,
        created_at=str(kb["created_at"]),
        updated_at=str(kb["updated_at"]),
    )


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(kb_id: str, body: KnowledgeBaseUpdate, request: Request) -> KnowledgeBaseResponse:
    user = require_user(request)
    kb = _knowledge_bases.get(kb_id)
    if not kb or kb["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

    if body.name is not None:
        kb["name"] = body.name
    if body.description is not None:
        kb["description"] = body.description
    kb["updated_at"] = time.time()

    doc_count = sum(1 for d in _documents.values() if d["knowledge_base_id"] == kb_id)
    return KnowledgeBaseResponse(
        id=kb["id"],
        user_id=kb["user_id"],
        name=kb["name"],
        description=kb["description"],
        embedding_model=kb["embedding_model"],
        document_count=doc_count,
        created_at=str(kb["created_at"]),
        updated_at=str(kb["updated_at"]),
    )


@router.delete("/{kb_id}")
async def delete_knowledge_base(kb_id: str, request: Request) -> dict:
    user = require_user(request)
    kb = _knowledge_bases.get(kb_id)
    if not kb or kb["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

    for doc_id in list(_documents.keys()):
        if _documents[doc_id]["knowledge_base_id"] == kb_id:
            del _documents[doc_id]
            if doc_id in _document_chunks:
                del _document_chunks[doc_id]

    del _knowledge_bases[kb_id]
    logger.info(f"Knowledge base deleted: {kb_id}")
    return {"success": True, "message": f"Knowledge base {kb_id} deleted"}


@router.post("/{kb_id}/documents", response_model=DocumentResponse)
async def upload_document(kb_id: str, request: Request, file: UploadFile = File(...)) -> DocumentResponse:
    user = require_user(request)
    kb = _knowledge_bases.get(kb_id)
    if not kb or kb["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

    doc_id = str(uuid.uuid4())
    now = time.time()

    file_type = file.filename.split(".")[-1].lower() if file.filename else "unknown"
    allowed_types = ["pdf", "docx", "txt", "md", "csv"]
    if file_type not in allowed_types:
        raise HTTPException(status_code=422, detail=f"File type {file_type} not supported. Allowed: {allowed_types}")

    content = await file.read()
    file_size = len(content)

    doc = {
        "id": doc_id,
        "knowledge_base_id": kb_id,
        "original_name": file.filename or "unknown",
        "file_type": file_type,
        "file_size": file_size,
        "storage_path": f"/mnt/user-data/knowledge/{kb_id}/{doc_id}/{file.filename}",
        "status": "processing",
        "chunk_count": 0,
        "token_count": 0,
        "uploaded_at": now,
        "processed_at": None,
    }
    _documents[doc_id] = doc
    _document_chunks[doc_id] = []

    logger.info(f"Document uploaded: {doc_id} to knowledge base {kb_id}")

    doc["status"] = "ready"
    doc["processed_at"] = time.time()

    return DocumentResponse(
        id=doc["id"],
        knowledge_base_id=doc["knowledge_base_id"],
        original_name=doc["original_name"],
        file_type=doc["file_type"],
        file_size=doc["file_size"],
        status=doc["status"],
        chunk_count=doc["chunk_count"],
        token_count=doc["token_count"],
        uploaded_at=str(doc["uploaded_at"]),
        processed_at=str(doc["processed_at"]) if doc["processed_at"] else None,
    )


@router.get("/{kb_id}/documents", response_model=list[DocumentResponse])
async def list_documents(kb_id: str, request: Request) -> list[DocumentResponse]:
    user = require_user(request)
    kb = _knowledge_bases.get(kb_id)
    if not kb or kb["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

    result = []
    for doc in _documents.values():
        if doc["knowledge_base_id"] == kb_id:
            result.append(
                DocumentResponse(
                    id=doc["id"],
                    knowledge_base_id=doc["knowledge_base_id"],
                    original_name=doc["original_name"],
                    file_type=doc["file_type"],
                    file_size=doc["file_size"],
                    status=doc["status"],
                    chunk_count=doc["chunk_count"],
                    token_count=doc["token_count"],
                    uploaded_at=str(doc["uploaded_at"]),
                    processed_at=str(doc["processed_at"]) if doc["processed_at"] else None,
                )
            )
    result.sort(key=lambda x: x.uploaded_at, reverse=True)
    return result


@router.delete("/{kb_id}/documents/{doc_id}")
async def delete_document(kb_id: str, doc_id: str, request: Request) -> dict:
    user = require_user(request)
    kb = _knowledge_bases.get(kb_id)
    if not kb or kb["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

    doc = _documents.get(doc_id)
    if not doc or doc["knowledge_base_id"] != kb_id:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    if doc_id in _document_chunks:
        del _document_chunks[doc_id]
    del _documents[doc_id]

    logger.info(f"Document deleted: {doc_id}")
    return {"success": True, "message": f"Document {doc_id} deleted"}


@router.post("/{kb_id}/documents/{doc_id}/reindex")
async def reindex_document(kb_id: str, doc_id: str, request: Request) -> DocumentResponse:
    user = require_user(request)
    kb = _knowledge_bases.get(kb_id)
    if not kb or kb["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

    doc = _documents.get(doc_id)
    if not doc or doc["knowledge_base_id"] != kb_id:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    doc["status"] = "processing"
    doc["processed_at"] = None

    logger.info(f"Document reindex started: {doc_id}")

    doc["status"] = "ready"
    doc["processed_at"] = time.time()

    return DocumentResponse(
        id=doc["id"],
        knowledge_base_id=doc["knowledge_base_id"],
        original_name=doc["original_name"],
        file_type=doc["file_type"],
        file_size=doc["file_size"],
        status=doc["status"],
        chunk_count=doc["chunk_count"],
        token_count=doc["token_count"],
        uploaded_at=str(doc["uploaded_at"]),
        processed_at=str(doc["processed_at"]) if doc["processed_at"] else None,
    )


@router.post("/{kb_id}/search", response_model=SearchResponse)
async def semantic_search(kb_id: str, body: SearchRequest, request: Request) -> SearchResponse:
    user = require_user(request)
    kb = _knowledge_bases.get(kb_id)
    if not kb or kb["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Knowledge base {kb_id} not found")

    query_embedding = _calculate_embedding(body.query)

    all_chunks = []
    for doc_id, chunks in _document_chunks.items():
        doc = _documents.get(doc_id)
        if not doc or doc["knowledge_base_id"] != kb_id:
            continue
        for chunk in chunks:
            chunk_copy = dict(chunk)
            chunk_copy["document_id"] = doc_id
            chunk_copy["document_name"] = doc["original_name"]
            chunk_copy["embedding"] = _calculate_embedding(chunk.get("content", ""))
            chunk_copy["similarity"] = _calculate_similarity(query_embedding, chunk_copy["embedding"])
            all_chunks.append(chunk_copy)

    results = []
    for chunk in all_chunks:
        if chunk["similarity"] >= body.similarity_threshold:
            results.append(
                SearchResult(
                    document_id=chunk["document_id"],
                    document_name=chunk["document_name"],
                    chunk_content=chunk.get("content", ""),
                    similarity_score=chunk["similarity"],
                    metadata=chunk.get("metadata", {}),
                )
            )

    results.sort(key=lambda x: x.similarity_score, reverse=True)
    results = results[: body.top_k]

    return SearchResponse(
        results=results,
        query=body.query,
        knowledge_base_id=kb_id,
    )

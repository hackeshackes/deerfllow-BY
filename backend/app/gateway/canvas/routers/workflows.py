from __future__ import annotations

import asyncio
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.gateway.auth import AuthUser, require_owner_user, require_user
from app.gateway.canvas.executor import WorkflowExecutor
from app.gateway.canvas.models import (
    NodeKind,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
    WorkflowStatus,
)
from app.gateway.canvas.store import WorkflowStore
from app.gateway.canvas.versions import VersionManager

router = APIRouter(prefix="/api/workflows", tags=["canvas"])

# Module-level singletons; tests use configure()/reset_for_tests().
_store: WorkflowStore | None = None
_version_mgr: VersionManager | None = None
_executor: WorkflowExecutor | None = None


def configure(store: WorkflowStore, version_mgr: VersionManager, executor: WorkflowExecutor | None = None) -> None:
    global _store, _version_mgr, _executor
    _store = store
    _version_mgr = version_mgr
    _executor = executor


def reset_for_tests() -> None:
    global _store, _version_mgr, _executor
    _store = None
    _version_mgr = None
    _executor = None


def _dep_store() -> WorkflowStore:
    if _store is None:
        raise HTTPException(status_code=503, detail="canvas store not configured")
    return _store


def _dep_versions() -> VersionManager:
    if _version_mgr is None:
        raise HTTPException(status_code=503, detail="canvas version manager not configured")
    return _version_mgr


# ---- Pydantic schemas ----


class _NodeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    kind: NodeKind
    config: dict[str, Any] = Field(default_factory=dict)
    position: tuple[float, float] = (0.0, 0.0)


class _EdgeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    source_node_id: str
    target_node_id: str
    condition: str | None = None


class WorkflowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    workspace_id: str
    status: WorkflowStatus = WorkflowStatus.DRAFT
    nodes: list[_NodeIn] = Field(default_factory=list)
    edges: list[_EdgeIn] = Field(default_factory=list)


class WorkflowUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    status: WorkflowStatus | None = None
    nodes: list[_NodeIn] | None = None
    edges: list[_EdgeIn] | None = None


class WorkflowResponse(BaseModel):
    id: str
    name: str
    workspace_id: str
    status: WorkflowStatus
    version: int
    nodes: list[_NodeIn]
    edges: list[_EdgeIn]
    created_at: datetime
    updated_at: datetime


def _to_response(wf: Workflow) -> WorkflowResponse:
    return WorkflowResponse(
        id=wf.id,
        name=wf.name,
        workspace_id=wf.workspace_id,
        status=wf.status,
        version=wf.version,
        nodes=[_NodeIn(id=n.id, kind=n.kind, config=dict(n.config), position=n.position) for n in wf.nodes],
        edges=[_EdgeIn(id=e.id, source_node_id=e.source_node_id, target_node_id=e.target_node_id, condition=e.condition) for e in wf.edges],
        created_at=wf.created_at,
        updated_at=wf.updated_at,
    )


def _nodes_from_schema(items: list[_NodeIn]) -> tuple[WorkflowNode, ...]:
    return tuple(WorkflowNode(id=n.id, kind=n.kind, config=n.config, position=n.position) for n in items)


def _edges_from_schema(items: list[_EdgeIn]) -> tuple[WorkflowEdge, ...]:
    return tuple(WorkflowEdge(id=e.id, source_node_id=e.source_node_id, target_node_id=e.target_node_id, condition=e.condition) for e in items)


def _workflow_from_create(body: WorkflowCreate, wf_id: str) -> Workflow:
    now = datetime.now(UTC)
    return Workflow(
        id=wf_id,
        name=body.name,
        workspace_id=body.workspace_id,
        status=body.status,
        nodes=_nodes_from_schema(body.nodes),
        edges=_edges_from_schema(body.edges),
        version=1,
        created_at=now,
        updated_at=now,
    )


# ---- Routes ----


@router.get("", response_model=dict[str, list[WorkflowResponse]])
def list_workflows(
    workspace_id: str,
    user: AuthUser = Depends(require_user),
    store: WorkflowStore = Depends(_dep_store),
):
    items = store.list_by_workspace(workspace_id)
    return {"workflows": [_to_response(w) for w in items]}


@router.post("", response_model=WorkflowResponse, status_code=200)
def create_workflow(
    body: WorkflowCreate,
    user: AuthUser = Depends(require_owner_user),
    store: WorkflowStore = Depends(_dep_store),
    versions: VersionManager = Depends(_dep_versions),
):
    wf_id = uuid.uuid4().hex
    try:
        wf = _workflow_from_create(body, wf_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    saved = store.upsert(wf)
    versions.commit(saved)
    return _to_response(saved)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: str,
    user: AuthUser = Depends(require_user),
    store: WorkflowStore = Depends(_dep_store),
):
    wf = store.get(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    return _to_response(wf)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: str,
    body: WorkflowUpdate,
    user: AuthUser = Depends(require_user),
    store: WorkflowStore = Depends(_dep_store),
    versions: VersionManager = Depends(_dep_versions),
):
    current = store.get(workflow_id)
    if current is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    new_name = body.name if body.name is not None else current.name
    new_status = body.status if body.status is not None else current.status
    new_nodes = _nodes_from_schema(body.nodes) if body.nodes is not None else current.nodes
    new_edges = _edges_from_schema(body.edges) if body.edges is not None else current.edges
    try:
        updated = replace(
            current,
            name=new_name,
            status=new_status,
            nodes=new_nodes,
            edges=new_edges,
            updated_at=datetime.now(UTC),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    saved = store.upsert(updated)
    versions.commit(saved)
    return _to_response(saved)


@router.delete("/{workflow_id}", response_model=dict[str, bool])
def delete_workflow(
    workflow_id: str,
    user: AuthUser = Depends(require_user),
    store: WorkflowStore = Depends(_dep_store),
):
    store.delete(workflow_id)
    return {"success": True}


@router.get("/{workflow_id}/versions", response_model=dict[str, list[dict]])
def list_versions(
    workflow_id: str,
    user: AuthUser = Depends(require_user),
    store: WorkflowStore = Depends(_dep_store),
    versions: VersionManager = Depends(_dep_versions),
):
    if store.get(workflow_id) is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    return {
        "versions": [
            {
                "workflow_id": v.workflow_id,
                "version": v.version,
                "created_at": v.created_at.isoformat(),
                "snapshot": _to_response(v.snapshot).model_dump(mode="json"),
            }
            for v in versions.list_versions(workflow_id)
        ]
    }


@router.post("/{workflow_id}/rollback/{version}", response_model=WorkflowResponse)
def rollback(
    workflow_id: str,
    version: int,
    user: AuthUser = Depends(require_user),
    versions: VersionManager = Depends(_dep_versions),
):
    try:
        restored = versions.rollback(workflow_id, version)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(restored)


class _ExecuteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inputs: dict[str, Any] = Field(default_factory=dict)
    workspace_id: str


@router.post("/{workflow_id}/execute")
def execute_workflow(
    workflow_id: str,
    body: _ExecuteBody,
    user: AuthUser = Depends(require_user),
    store: WorkflowStore = Depends(_dep_store),
):
    wf = store.get(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    if wf.workspace_id != body.workspace_id:
        raise HTTPException(status_code=403, detail={"error": {"code": "NOT_WORKSPACE_MEMBER"}})
    if _executor is None:
        raise HTTPException(status_code=503, detail="executor not configured")

    execution = asyncio.run(_executor.execute(wf, body.inputs))
    return {
        "workflow_id": execution.workflow_id,
        "workflow_version": execution.workflow_version,
        "outputs": execution.outputs,
        "steps": [
            {
                "node_id": s.node_id,
                "status": s.status,
                "started_at": s.started_at.isoformat(),
                "ended_at": s.ended_at.isoformat(),
                "outputs": s.outputs,
                "error": s.error,
            }
            for s in execution.steps
        ],
        "total_tokens": execution.total_tokens,
        "failed_node_id": execution.failed_node_id,
    }

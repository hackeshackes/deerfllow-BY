"""Frozen dataclasses describing the workflow canvas domain.

A `Workflow` is an immutable directed graph of `WorkflowNode`s connected
by `WorkflowEdge`s. All invariants are enforced in `__post_init__` so
that any code that constructs a `Workflow` — API handlers, the version
manager, the in-memory store, the executor — sees the same shape.

v1.6.x surface (Task A1):

* `NodeKind` / `WorkflowStatus` — str-enums for safe serialisation.
* `WorkflowNode` — frozen, validates `kind` membership, and applies
  per-kind config rules (LOOP iterations bound, BRANCH requires a
  non-empty `condition` string).
* `WorkflowEdge` — frozen, holds the optional edge-level condition.
* `Workflow` — frozen, rejects empty `name`/`workspace_id`, validates
  that every edge references a real node, and exposes created/updated
  timestamps plus a monotonically increasing `version`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class NodeKind(str, Enum):
    AGENT = "agent"
    TOOL = "tool"
    PROMPT = "prompt"
    BRANCH = "branch"
    LOOP = "loop"


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class WorkflowNode:
    id: str
    kind: NodeKind
    config: Mapping[str, Any]
    position: tuple[float, float]

    def __post_init__(self) -> None:
        # Accept either the enum or its underlying string value (string
        # values are useful when nodes are reconstructed from JSON).
        valid_kinds = {k.value for k in NodeKind}
        if not isinstance(self.kind, NodeKind) and self.kind not in valid_kinds:
            raise ValueError(f"Unknown NodeKind: {self.kind!r}")

        is_loop = self.kind is NodeKind.LOOP or self.kind == NodeKind.LOOP.value
        if is_loop:
            iterations = self.config.get("iterations", 1)
            if not isinstance(iterations, int) or isinstance(iterations, bool):
                raise ValueError("LOOP iterations must be int in [1, 1000]")
            if iterations < 1 or iterations > 1000:
                raise ValueError("LOOP iterations must be int in [1, 1000]")

        is_branch = self.kind is NodeKind.BRANCH or self.kind == NodeKind.BRANCH.value
        if is_branch:
            condition = self.config.get("condition")
            if not isinstance(condition, str) or not condition.strip():
                raise ValueError("BRANCH requires non-empty 'condition' string")


@dataclass(frozen=True)
class WorkflowEdge:
    id: str
    source_node_id: str
    target_node_id: str
    condition: str | None = None


@dataclass(frozen=True)
class Workflow:
    id: str
    name: str
    workspace_id: str
    status: WorkflowStatus = WorkflowStatus.DRAFT
    nodes: tuple[WorkflowNode, ...] = ()
    edges: tuple[WorkflowEdge, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    version: int = 1

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Workflow name must not be empty")
        if not self.workspace_id or not self.workspace_id.strip():
            raise ValueError("workspace_id is required")
        node_ids = {n.id for n in self.nodes}
        for edge in self.edges:
            if edge.source_node_id not in node_ids or edge.target_node_id not in node_ids:
                raise ValueError(f"Edge {edge.id} references unknown node")

"""``WorkflowExecutor`` — linear composition of node executors (Task A7).

The executor owns no runtime semantics of its own: each ``NodeKind`` is
delegated to a registered executor that obeys the ``NodeExecutor``
Protocol (`nodes/base.py`). The executor's job is:

* Iterate ``Workflow.nodes`` in declared order (graph traversal with
  cycle detection is a v1.7+ concern; today the workflow author is
  responsible for declaring nodes in execution order).
* Look up the executor for each ``node.kind``; if missing, mark the
  step failed (and optionally abort when ``fail_fast=True``).
* Convert ``NodeOutput.error`` into a failed ``ExecutionStep`` so the
  step record is consistent regardless of where the failure surfaced.
* Propagate successful outputs downstream so a later prompt can
  reference them as ``{{var}}`` inputs (``setdefault`` preserves any
  workflow-level input overrides).
* Surface aggregate state — ``WorkflowExecution.outputs`` is
  ``node_id -> outputs`` and ``failed_node_id`` is set on first failure
  in ``fail_fast`` mode.

The ``loop_wall_clock_seconds`` budget is reserved for v1.7 when the
loop sentinel grows real loop-body execution. v1.6.x loop nodes only
return their iteration count.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .models import NodeKind, Workflow
from .nodes.base import NodeOutput


@dataclass(frozen=True)
class ExecutionStep:
    """Record of a single node invocation within a workflow run."""

    node_id: str
    started_at: datetime
    ended_at: datetime
    status: str  # "ok" | "failed" | "skipped"
    outputs: Mapping[str, Any]
    error: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowExecution:
    """Aggregate result of running a workflow end-to-end."""

    workflow_id: str
    workflow_version: int
    started_at: datetime
    ended_at: datetime
    steps: tuple[ExecutionStep, ...]
    outputs: Mapping[str, Any]
    total_tokens: int = 0
    failed_node_id: str | None = None


class WorkflowExecutor:
    """Compose node executors into a linear workflow run.

    The executor is intentionally thin: it does not own tool/auth/sandbox
    state, only the registry that maps ``NodeKind`` to a concrete
    ``NodeExecutor`` implementation.
    """

    def __init__(
        self,
        node_executors: Mapping[NodeKind, Any],
        fail_fast: bool = False,
        loop_wall_clock_seconds: int = 60,
    ) -> None:
        self._executors = dict(node_executors)
        self._fail_fast = fail_fast
        self._loop_timeout = loop_wall_clock_seconds

    async def execute(
        self,
        workflow: Workflow,
        inputs: Mapping[str, Any],
    ) -> WorkflowExecution:
        """Run ``workflow`` linearly and return the aggregate execution.

        Parameters
        ----------
        workflow:
            Frozen workflow graph. Nodes are executed in declared order.
        inputs:
            Initial inputs available to every node. Per-step outputs are
            ``setdefault``-merged into the running input set so explicit
            workflow-level inputs win over upstream outputs.
        """
        started = datetime.now(UTC)
        steps: list[ExecutionStep] = []
        outputs: dict[str, Any] = {}
        failed_node_id: str | None = None
        current_inputs: dict[str, Any] = dict(inputs)
        # Linear execution assumes nodes are ordered in ``workflow.nodes``.
        # Edges determine branch routing only for BRANCH nodes (full graph
        # traversal with cycle detection is a v1.7+ enhancement).
        for node in workflow.nodes:
            step_started = datetime.now(UTC)
            executor = self._executors.get(node.kind)
            if executor is None:
                step = ExecutionStep(
                    node_id=node.id,
                    started_at=step_started,
                    ended_at=datetime.now(UTC),
                    status="failed",
                    outputs={},
                    error=f"no executor registered for kind {node.kind!r}",
                )
                steps.append(step)
                if self._fail_fast:
                    failed_node_id = node.id
                    break
                continue
            try:
                out: NodeOutput = await executor.execute(node.config, current_inputs)
            except Exception as exc:  # noqa: BLE001 — surface as NodeOutput.error
                out = NodeOutput(outputs={}, error=f"node exception: {exc}")
            step_ended = datetime.now(UTC)
            if out.error is not None:
                steps.append(
                    ExecutionStep(
                        node_id=node.id,
                        started_at=step_started,
                        ended_at=step_ended,
                        status="failed",
                        outputs={},
                        error=out.error,
                        metadata=out.metadata,
                    )
                )
                if self._fail_fast:
                    failed_node_id = node.id
                    break
                continue
            steps.append(
                ExecutionStep(
                    node_id=node.id,
                    started_at=step_started,
                    ended_at=step_ended,
                    status="ok",
                    outputs=out.outputs,
                    metadata=out.metadata,
                )
            )
            outputs[node.id] = out.outputs
            # Propagate outputs into inputs for downstream nodes (setdefault
            # preserves any explicit workflow-level inputs).
            for k, v in out.outputs.items():
                current_inputs.setdefault(k, v)
        ended = datetime.now(UTC)
        return WorkflowExecution(
            workflow_id=workflow.id,
            workflow_version=workflow.version,
            started_at=started,
            ended_at=ended,
            steps=tuple(steps),
            outputs=outputs,
            failed_node_id=failed_node_id,
        )

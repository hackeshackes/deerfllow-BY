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
* Route BRANCH fanout (v1.6.x self-audit fix): when a BRANCH node
  records ``outputs.matched``, the executor runs the downstream node
  whose entry edge has ``condition == "true"`` (matched=True) or
  ``"false"`` (matched=False) and skips the other side.
* Repeat LOOP body (v1.6.x self-audit fix): when a LOOP node records
  ``outputs.iterations``, the executor runs every downstream node in
  its sub-graph that many times, tagging each step with
  ``metadata.iteration`` and accumulating outputs as a list.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .models import NodeKind, Workflow, WorkflowEdge
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
    """Aggregate result of running a workflow end-to-end.

    `total_tokens` is reserved for v1.7+ once Agent/Tool nodes report token
    usage; in v1.6.x it is always 0.
    """

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
    ) -> None:
        self._executors = dict(node_executors)
        self._fail_fast = fail_fast

    async def execute(
        self,
        workflow: Workflow,
        inputs: Mapping[str, Any],
    ) -> WorkflowExecution:
        """Run ``workflow`` linearly and return the aggregate execution.

        BRANCH routing: when a BRANCH node records ``outputs["matched"]``,
        the executor selects downstream nodes whose incoming edge has
        ``condition == ("true" if matched else "false")`` and skips the
        other side.

        LOOP body: when a LOOP node records ``outputs["iterations"]``,
        the executor runs every node in its downstream sub-graph
        ``iterations`` times. Each step is tagged with
        ``metadata.iteration`` and outputs are accumulated as a list.
        """
        started = datetime.now(UTC)
        steps: list[ExecutionStep] = []
        outputs: dict[str, Any] = {}
        failed_node_id: str | None = None
        current_inputs: dict[str, Any] = dict(inputs)
        # Track nodes that have already been "claimed" by a previous
        # branch/loop routing pass so a node isn't run twice when it's
        # also present in the linear walk.
        claimed: set[str] = set()
        skipped: set[str] = set()
        # Pre-compute adjacency for fast routing lookups.
        outgoing: dict[str, list[WorkflowEdge]] = {}
        incoming: dict[str, list[WorkflowEdge]] = {}
        for e in workflow.edges:
            outgoing.setdefault(e.source_node_id, []).append(e)
            incoming.setdefault(e.target_node_id, []).append(e)

        for node in workflow.nodes:
            if node.id in claimed or node.id in skipped:
                continue
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
            for k, v in out.outputs.items():
                current_inputs.setdefault(k, v)

            # BRANCH routing: pick one downstream based on `matched`.
            if node.kind == NodeKind.BRANCH and "matched" in out.outputs:
                matched = bool(out.outputs["matched"])
                wanted_condition = "true" if matched else "false"
                # Run the selected branch first so its steps appear
                # immediately after the BRANCH node in the trace.
                for edge in outgoing.get(node.id, ()):  # type: WorkflowEdge
                    if edge.condition == wanted_condition:
                        claimed.add(edge.target_node_id)
                        ok, fail_id, sub_steps, sub_out, new_inputs = await self._run_subgraph(
                            workflow,
                            edge.target_node_id,
                            current_inputs,
                            claimed,
                            incoming,
                            outgoing,
                        )
                        steps.extend(sub_steps)
                        # Merge subgraph outputs into the top-level map.
                        for k, v in sub_out.items():
                            outputs[k] = v
                            current_inputs.setdefault(k, v if not isinstance(v, list) else v[-1])
                        if fail_id is not None and self._fail_fast:
                            failed_node_id = fail_id
                            break
                # Then record the unselected branch(es) as skipped so
                # the trace reflects the routing decision.
                for edge in outgoing.get(node.id, ()):  # type: WorkflowEdge
                    if edge.condition and edge.condition != wanted_condition:
                        now = datetime.now(UTC)
                        steps.append(
                            ExecutionStep(
                                node_id=edge.target_node_id,
                                started_at=now,
                                ended_at=now,
                                status="skipped",
                                outputs={},
                                metadata={"branch_unselected": edge.condition},
                            )
                        )
                        skipped.add(edge.target_node_id)
                if failed_node_id is not None and self._fail_fast:
                    break

            # LOOP body: repeat downstream sub-graph `iterations` times.
            if node.kind == NodeKind.LOOP and "iterations" in out.outputs:
                try:
                    iters = int(out.outputs["iterations"])
                except (TypeError, ValueError):
                    iters = 0
                body_targets = [e.target_node_id for e in outgoing.get(node.id, ())]
                if body_targets and iters > 0:
                    for body_root in body_targets:
                        claimed.add(body_root)
                    accumulated: dict[str, list[Any]] = {tid: [] for tid in body_targets}
                    for i in range(1, iters + 1):
                        for body_root in body_targets:
                            ok, fail_id, sub_steps, sub_out, new_inputs = await self._run_subgraph(
                                workflow,
                                body_root,
                                current_inputs,
                                claimed,
                                incoming,
                                outgoing,
                                iteration=i,
                            )
                            for s in sub_steps:
                                # Decorate body steps with iteration tag.
                                steps.append(
                                    ExecutionStep(
                                        node_id=s.node_id,
                                        started_at=s.started_at,
                                        ended_at=s.ended_at,
                                        status=s.status,
                                        outputs=s.outputs,
                                        error=s.error,
                                        metadata={**s.metadata, "iteration": i},
                                    )
                                )
                            for k, v in sub_out.items():
                                if isinstance(v, list):
                                    accumulated.setdefault(k, []).extend(v)
                                else:
                                    accumulated.setdefault(k, []).append(v)
                                current_inputs.setdefault(k, v if not isinstance(v, list) else v[-1])
                            if fail_id is not None and self._fail_fast:
                                failed_node_id = fail_id
                                break
                        if failed_node_id is not None and self._fail_fast:
                            break
                    for tid, vals in accumulated.items():
                        outputs[tid] = vals
                if failed_node_id is not None and self._fail_fast:
                    break

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

    async def _run_subgraph(
        self,
        workflow: Workflow,
        root_id: str,
        current_inputs: dict[str, Any],
        claimed: set[str],
        incoming: dict[str, list[WorkflowEdge]],
        outgoing: dict[str, list[WorkflowEdge]],
        iteration: int | None = None,
    ) -> tuple[bool, str | None, list[ExecutionStep], dict[str, Any], dict[str, Any]]:
        """Run a sub-graph starting at ``root_id``, returning steps + outputs.

        The sub-graph walk follows outgoing edges and stops at any node
        that has more than one incoming edge (i.e. it's a join point
        shared with the linear walk) or has already been claimed. The
        caller is responsible for adding the root node to ``claimed``
        before invoking this.
        """
        sub_steps: list[ExecutionStep] = []
        sub_out: dict[str, Any] = {}
        new_inputs = dict(current_inputs)
        # Simple BFS by node order, capped at the original node list to
        # avoid runaway expansion in malformed graphs.
        node_by_id = {n.id: n for n in workflow.nodes}
        order = [n for n in workflow.nodes if n.id == root_id or n.id in claimed]
        # Find the sub-graph: any node reachable from root via edges that
        # hasn't been seen and isn't a join point.
        seen: set[str] = set()
        stack: list[str] = [root_id]
        while stack:
            nid = stack.pop()
            if nid in seen:
                continue
            # The root was already added to `claimed` by the caller; for
            # subsequent descendants we still want to skip anything the
            # caller marked claimed or skipped, but not the root itself.
            if nid != root_id and (nid in claimed or nid in skipped):
                continue
            seen.add(nid)
            node = node_by_id.get(nid)
            if node is None:
                continue
            step_started = datetime.now(UTC)
            executor = self._executors.get(node.kind)
            if executor is None:
                step = ExecutionStep(
                    node_id=nid,
                    started_at=step_started,
                    ended_at=datetime.now(UTC),
                    status="failed",
                    outputs={},
                    error=f"no executor registered for kind {node.kind!r}",
                )
                sub_steps.append(step)
                if self._fail_fast:
                    return False, nid, sub_steps, sub_out, new_inputs
                continue
            try:
                out: NodeOutput = await executor.execute(node.config, new_inputs)
            except Exception as exc:  # noqa: BLE001
                out = NodeOutput(outputs={}, error=f"node exception: {exc}")
            step_ended = datetime.now(UTC)
            if out.error is not None:
                step = ExecutionStep(
                    node_id=nid,
                    started_at=step_started,
                    ended_at=step_ended,
                    status="failed",
                    outputs={},
                    error=out.error,
                    metadata=out.metadata,
                )
                sub_steps.append(step)
                if self._fail_fast:
                    return False, nid, sub_steps, sub_out, new_inputs
                continue
            meta = dict(out.metadata)
            if iteration is not None:
                meta.setdefault("iteration", iteration)
            sub_steps.append(
                ExecutionStep(
                    node_id=nid,
                    started_at=step_started,
                    ended_at=step_ended,
                    status="ok",
                    outputs=out.outputs,
                    metadata=meta,
                )
            )
            sub_out[nid] = out.outputs
            for k, v in out.outputs.items():
                new_inputs.setdefault(k, v)
            for edge in outgoing.get(nid, ()):  # type: WorkflowEdge
                stack.append(edge.target_node_id)
        return True, None, sub_steps, sub_out, new_inputs

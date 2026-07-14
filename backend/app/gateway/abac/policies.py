"""ABAC policy presets (v1.6.1).

Two reusable policies that cover the v1.6.1 simplification:

* ``OwnerOnlyPolicy`` — only subjects with ``role == "owner"`` may
  perform the action. Equivalent to the v1.5.4 RBAC v2 admin gate.
* ``WorkspaceMemberPolicy`` — owners are always allowed; members
  are allowed only when the resource's ``workspace_id`` is in the
  subject's ``workspaces`` attribute list.

These policies know nothing about Thread vs Workflow vs Connector;
they evaluate against the generic ``(subject, resource, action)``
tuple the v1.6.1 evaluator takes. The route that owns the
authorization call (publish router, workflow router) builds the
``Subject`` and ``Resource`` from its request context before
calling ``abac.evaluate``.
"""

from __future__ import annotations

from .evaluator import AttributePolicy, Operator


class OwnerOnlyPolicy(AttributePolicy):
    """Owner-only gate. Applies to any verb; only owners match."""

    def __init__(self, *, verbs=("write", "publish", "execute", "delete", "rollback")) -> None:
        super().__init__(
            name="owner-only",
            applies_to=tuple((v,) for v in verbs),
            operators=(Operator.equals("subject.role", "owner"),),
            combinator="all_of",
            effect="allow",
        )


class WorkspaceMemberPolicy(AttributePolicy):
    """Role-aware workspace gate.

    * owners → always allowed (equivalent to Admins in v1.5.4 RBAC v2)
    * members → allowed only when ``resource.workspace_id`` is in
      ``subject.workspaces``

    Implementor's note: we represent this as TWO predicates joined
    with ``any_of`` rather than nesting branches, so the fixed-AST
    evaluator handles it without needing a dedicated ``or`` operator.
    """

    def __init__(
        self,
        *,
        verbs=("read", "execute", "publish", "write"),
    ) -> None:
        super().__init__(
            name="workspace-member",
            applies_to=tuple((v,) for v in verbs),
            operators=(
                Operator.equals("subject.role", "owner"),
                Operator.in_(
                    "resource.workspace_id",
                    "subject.workspaces",
                ),
            ),
            combinator="any_of",
            effect="allow",
        )

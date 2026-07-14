"""ABAC simplified — evaluator (v1.6.1).

Scope of this evaluator is intentionally narrow. It is NOT a full
ABAC engine: it does not implement RFC-aligned XACML, does not
evaluate user-supplied code, and does not chain across policy
sources at runtime. The goal is "good enough to skip the v1.6.x
debt" — give callers a fixed operator set so future policies can
be authored declaratively without escalating to a real policy
engine.

Design notes:

* Operators form a fixed AST — ``equals``, ``in``, ``all_of``,
  ``any_of``, ``not``. NO ``eval`` / ``exec`` of caller-supplied
  code; this matches the branch-node contract used elsewhere in
  v1.6.x and ensures the audit story is "we never run user code"
  even when a future maintainer adds new operators.
* Path lookups use ``dotted.path`` strings (e.g.
  ``subject.role`` or ``resource.workspace_id``); expressions
  resolve first against the Subject, then the Resource, then the
  Action.
* The first policy whose ``applies_to`` matches AND whose operator
  AST evaluates to ``True`` returns its ``effect`` (allow or deny).
  Policies not applicable to the action are skipped. With no
  matching policy, the default is ``deny`` (fail-closed).
* Each policy carries a ``name`` for audit logs; the decision
  includes the matched policy's name.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

# ---- Domain value objects ----


@dataclass(frozen=True)
class Subject:
    """A user performing the action."""

    id: str
    role: str
    attrs: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Resource:
    """The object being acted on."""

    type: str
    id: str
    attrs: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    """A verb (e.g. ``read``, ``write``, ``execute``, ``publish``).

    Keep this thin — a single ``verb`` string is enough for v1.6.1
    routing. If v1.7+ needs more (e.g. ``publish.target=ws-b``),
    expand here without breaking the public contract.
    """

    verb: str


# ---- Decision + operators ----


@dataclass(frozen=True)
class AbacDecision:
    """Result of an evaluation."""

    allowed: bool
    reason: str
    matched_policy: str | None = None


@dataclass(frozen=True)
class Operator:
    """Single comparison node. Stored as a small dataclass instead of
    a dict-of-dicts so the AST shape is statically typed and easy
    to validate in tests.

    Resolution rules:

    * ``lhs`` is a dotted path looked up against the (subject,
      resource, action) triple in that order. ``subject.role``
      resolves first; ``resource.workspace_id`` second;
      ``action.verb`` third.
    * ``kind == "equals"`` compares ``lhs`` to ``rhs`` exactly
      (``==``); both must be defined for the comparison to succeed.
    * ``kind == "in"`` returns ``True`` iff ``lhs`` is a member of
      ``rhs``. ``rhs`` may be a list (literal) or a dotted path
      resolving to a list. Membership is ``in``-style, with strings
      only by default — type warnings fall through as ``False``.
    """

    kind: str
    lhs: str
    rhs: Any = None

    @classmethod
    def equals(cls, lhs: str, rhs: Any) -> Operator:
        return cls(kind="equals", lhs=lhs, rhs=rhs)

    @classmethod
    def in_(cls, lhs: str, rhs: Any) -> Operator:
        return cls(kind="in", lhs=lhs, rhs=rhs)


def _resolve_path(path: str, subject, resource, action):
    """Resolve a dotted path against the (subject, resource, action)
    triple. First segment chooses the namespace; subsequent
    segments index into ``attrs`` for domain objects (Subject /
    Resource) and into the namespace object's direct attributes
    for Action.

    Fallback: if a Subject / Resource attribute lookup misses on the
    dataclass field, the resolver also tries ``attrs[segment]`` —
    this lets policies write ``subject.workspaces`` and find a key
    declared under ``Subject.attrs["workspaces"]`` without forcing
    every caller to reach into ``subject.attrs`` explicitly.
    """
    parts = path.split(".")
    if not parts:
        return None
    head, rest = parts[0], parts[1:]
    if head == "subject":
        current: Any = subject
    elif head == "resource":
        current = resource
    elif head == "action":
        current = action
    else:
        return None
    for segment in rest:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(segment)
            continue
        # Subject / Resource carry both direct fields (id / role /
        # type) and an ``attrs`` dict for dynamic data. Resolve
        # direct fields first, then attrs as a fallback so
        # ``subject.workspaces`` finds ``attrs["workspaces"]``.
        direct = getattr(current, segment, _MISSING)
        if direct is not _MISSING:
            current = direct
            continue
        attr_map = getattr(current, "attrs", None)
        if isinstance(attr_map, dict) and segment in attr_map:
            current = attr_map[segment]
            continue
        return None
    return current


_MISSING = object()


def _eval_operator(op: Operator, subject, resource, action) -> bool:
    lhs = _resolve_path(op.lhs, subject, resource, action)
    if op.kind == "equals":
        # ``None`` is a valid sentinel: an equals comparison against
        # ``None`` only succeeds when the LHS path resolves to None.
        # This is how ``equals("subject.role", "owner")`` correctly
        # fails when the subject has no role attribute.
        return op.rhs is not None and lhs is not None and op.rhs == lhs
    if op.kind == "in":
        if isinstance(op.rhs, str) and "." in op.rhs:
            rhs = _resolve_path(op.rhs, subject, resource, action)
        else:
            rhs = op.rhs
        if not isinstance(rhs, (list, tuple, set, frozenset)):
            return False
        return lhs in rhs
    return False


@dataclass(frozen=True)
class AttributePolicy:
    """A single ABAC rule applied to a (subject, resource, action) triple.

    A policy matches when its ``applies_to`` action verbs include the
    current ``action.verb`` AND its operator AST evaluates to True.
    The matching effect (``allow`` / ``deny``) is then returned. If
    no policy matches, the evaluator fails closed (deny).

    ``combinator``: ``"all_of"`` requires every operator to pass;
    ``"any_of"`` requires at least one. Empty operators list with
    ``all_of`` means "always pass" — useful for a blanket allow
    default; empty with ``any_of`` means "never pass".
    """

    name: str
    applies_to: tuple[tuple[str, ...], ...]
    operators: tuple[Operator, ...]
    combinator: str = "all_of"
    effect: str = "allow"

    def matches_action(self, action: Action) -> bool:
        if not self.applies_to:
            return True  # policy applies to all verbs
        for verbs in self.applies_to:
            if action.verb in verbs:
                return True
        return False

    def evaluate(self, subject, resource, action) -> bool:
        if not self.operators:
            return self.combinator == "all_of"
        results = [_eval_operator(op, subject, resource, action) for op in self.operators]
        if self.combinator == "all_of":
            return all(results)
        if self.combinator == "any_of":
            return any(results)
        return False


# ---- Top-level dispatch ----


PolicyList = Iterable[AttributePolicy]


def evaluate(
    *,
    subject: Subject,
    resource: Resource,
    action: Action,
    policies: PolicyList,
) -> AbacDecision:
    """Return the first matching policy's effect (deny/allow) or deny
    when nothing matches. Fail-closed by design — a missing policy
    must NOT silently allow access.
    """
    for policy in policies:
        if not policy.matches_action(action):
            continue
        if policy.evaluate(subject, resource, action):
            allowed = policy.effect == "allow"
            return AbacDecision(
                allowed=allowed,
                reason=f"{policy.effect} via {policy.name}",
                matched_policy=policy.name,
            )
    return AbacDecision(allowed=False, reason="no matching policy", matched_policy=None)

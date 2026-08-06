"""ABAC simplified (v1.6.1 P1) — public surface.

See ``app.gateway.abac.evaluator`` and ``app.gateway.abac.policies``
for the executable parts. This package is the catch-all so callers
that only need the public types can ``from app.gateway.abac import ...``
without knowing which submodule hosts them.
"""
from __future__ import annotations

from .evaluator import (
    AbacDecision,
    Action,
    AttributePolicy,
    Operator,
    Resource,
    Subject,
    evaluate,
)
from .policies import OwnerOnlyPolicy, WorkspaceMemberPolicy
from .policies_file import PoliciesCache, load_policies_file, resolve_policies

__all__ = [
    "AbacDecision",
    "Action",
    "AttributePolicy",
    "Operator",
    "OwnerOnlyPolicy",
    "PoliciesCache",
    "Resource",
    "Subject",
    "WorkspaceMemberPolicy",
    "evaluate",
    "load_policies_file",
    "resolve_policies",
]

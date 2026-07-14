"""Tests for the v1.6.1 ABAC simplified scope.

Closes the v1.6.0-canvas backlog item: ABAC was deferred entirely
because the existing role-string RBAC is sufficient for the canvas
authorization checks in v1.6.x. The v1.6.1 follow-up adds a minimal
ABAC surface so future per-resource / per-action policies can be
written without re-architecting the authorization layer.

Scope of the simplification (documented in the design §"ABAC
simplified"):

* ``Subject`` / ``Resource`` / ``Action`` dataclasses — plain
  containers, no behavior. Concrete types (e.g. ``WorkflowResource``,
  ``ThreadResource``) live where they make sense — we pass-through
  the base types here to avoid forcing every domain model to inherit
  from a single ``Resource`` class.
* ``AttributePolicy`` — a fixed AST of ``equals`` / ``in`` /
  ``all_of`` / ``any_of`` / ``not`` operators. NO user-supplied code
  evaluation: the same approach taken by the canvas branch node.
* ``AbacEvaluator`` — takes a list of policies plus a (subject,
  resource, action) tuple and returns the first matching policy's
  decision (allow/deny), with a default-deny fallback.
* Wire-up: two narrow use cases — workflow publish to another
  workspace and canvas workflow execute — are routed through the
  evaluator with policies attached.
"""

from __future__ import annotations

from app.gateway.abac import (
    Action,
    AttributePolicy,
    Operator,
    Resource,
    Subject,
    evaluate,
)
from app.gateway.abac.policies import (
    OwnerOnlyPolicy,
    WorkspaceMemberPolicy,
)

# ---- Pure evaluator tests ----


def test_evaluator_default_denies_when_no_policies_match():
    s = Subject(id="u-1", role="member", attrs={})
    r = Resource(type="workflow", id="w-1", attrs={"workspace_id": "ws-a"})
    a = Action(verb="execute")
    decision = evaluate(subject=s, resource=r, action=a, policies=[])
    assert decision.allowed is False
    assert decision.reason == "no matching policy"


def test_evaluator_allows_on_owner_only_policy_for_owner():
    s = Subject(id="u-1", role="owner", attrs={})
    r = Resource(type="workflow", id="w-1", attrs={"workspace_id": "ws-a"})
    a = Action(verb="execute")
    decision = evaluate(
        subject=s,
        resource=r,
        action=a,
        policies=[OwnerOnlyPolicy()],
    )
    assert decision.allowed is True
    assert decision.reason is not None


def test_evaluator_denies_on_owner_only_policy_for_member():
    s = Subject(id="u-2", role="member", attrs={})
    r = Resource(type="workflow", id="w-1", attrs={"workspace_id": "ws-a"})
    a = Action(verb="execute")
    decision = evaluate(
        subject=s,
        resource=r,
        action=a,
        policies=[OwnerOnlyPolicy()],
    )
    assert decision.allowed is False


def test_workspace_member_policy_allows_member_with_matching_workspace():
    s = Subject(id="u-2", role="member", attrs={"workspaces": ["ws-a", "ws-b"]})
    r = Resource(type="workflow", id="w-1", attrs={"workspace_id": "ws-a"})
    a = Action(verb="execute")
    decision = evaluate(
        subject=s,
        resource=r,
        action=a,
        policies=[WorkspaceMemberPolicy()],
    )
    assert decision.allowed is True


def test_workspace_member_policy_denies_member_with_unrelated_workspace():
    s = Subject(id="u-2", role="member", attrs={"workspaces": ["ws-z"]})
    r = Resource(type="workflow", id="w-1", attrs={"workspace_id": "ws-a"})
    a = Action(verb="execute")
    decision = evaluate(
        subject=s,
        resource=r,
        action=a,
        policies=[WorkspaceMemberPolicy()],
    )
    assert decision.allowed is False


def test_workspace_member_policy_allows_owner_regardless_of_workspace_list():
    """Owners get a pass on WorkspaceMemberPolicy — equivalent to
    Admins in v1.5.4 RBAC v2. This is the only place the policy
    branches on subject.role: everything else uses the subject
    attribute list."""
    s = Subject(id="u-1", role="owner", attrs={"workspaces": []})
    r = Resource(type="workflow", id="w-1", attrs={"workspace_id": "ws-a"})
    a = Action(verb="execute")
    decision = evaluate(
        subject=s,
        resource=r,
        action=a,
        policies=[WorkspaceMemberPolicy()],
    )
    assert decision.allowed is True


def test_custom_policy_with_equals_operator():
    """Lock down the evaluator's AST grammar — no Python eval, just
    fixed operators — so callers cannot trick it into running code."""
    # A policy: allow member execute only when resource.tag == "vip".
    vip_policy = AttributePolicy(
        name="vip-members-execute",
        applies_to=(("execute",),),
        operators=(
            Operator.equals("subject.role", "member"),
            Operator.equals("resource.tag", "vip"),
        ),
        effect="allow",
    )
    s_member_vip = Subject(id="u", role="member", attrs={})
    s_member_normal = Subject(id="u", role="member", attrs={})
    r_vip = Resource(type="workflow", id="w", attrs={"tag": "vip"})
    r_normal = Resource(type="workflow", id="w", attrs={"tag": "draft"})

    assert evaluate(
        subject=s_member_vip,
        resource=r_vip,
        action=Action(verb="execute"),
        policies=[vip_policy],
    ).allowed is True

    assert (
        evaluate(
            subject=s_member_normal,
            resource=r_normal,
            action=Action(verb="execute"),
            policies=[vip_policy],
        ).allowed
        is False
    )


def test_custom_policy_with_all_of_combinator():
    """The all_of combinator requires every operator to pass."""
    policy = AttributePolicy(
        name="member-in-workspace",
        applies_to=(("execute",),),
        operators=(
            Operator.equals("subject.role", "member"),
            Operator.in_("resource.workspace_id", "subject.workspaces"),
        ),
        combinator="all_of",
        effect="allow",
    )
    s_match = Subject(
        id="u", role="member", attrs={"workspaces": ["ws-a", "ws-b"]}
    )
    s_nomatch = Subject(id="u", role="member", attrs={"workspaces": []})
    r = Resource(type="workflow", id="w", attrs={"workspace_id": "ws-a"})

    a = Action(verb="execute")
    assert (
        evaluate(subject=s_match, resource=r, action=a, policies=[policy]).allowed
        is True
    )
    assert (
        evaluate(subject=s_nomatch, resource=r, action=a, policies=[policy]).allowed
        is False
    )


def test_first_matching_policy_wins():
    """When multiple policies match, the FIRST one (allow or deny)
    wins — explicit deny takes precedence over later allows when
    defined as a deny policy."""
    allow_a = AttributePolicy(
        name="allow-all-execute",
        applies_to=(("execute",),),
        operators=(),
        combinator="all_of",
        effect="allow",
    )
    deny_b = AttributePolicy(
        name="deny-archived",
        applies_to=(("execute",),),
        operators=(Operator.equals("resource.status", "archived"),),
        combinator="all_of",
        effect="deny",
    )
    s = Subject(id="u", role="owner", attrs={})
    r_active = Resource(type="workflow", id="w", attrs={"status": "draft"})
    r_archived = Resource(type="workflow", id="w", attrs={"status": "archived"})

    # active → first policy (allow-all) wins
    assert (
        evaluate(
            subject=s,
            resource=r_active,
            action=Action(verb="execute"),
            policies=[allow_a, deny_b],
        ).allowed
        is True
    )
    # archived → deny_b matches first because it precedes allow_a is
    # not the case; allow_a has no operators so it always passes —
    # so actually allow_a wins and the request is allowed. To prove
    # deny-second-wins we swap the order:

    assert (
        evaluate(
            subject=s,
            resource=r_archived,
            action=Action(verb="execute"),
            policies=[deny_b, allow_a],
        ).allowed
        is False
    )

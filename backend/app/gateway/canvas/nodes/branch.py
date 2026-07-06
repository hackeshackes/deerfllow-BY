from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .base import NodeOutput

_OPS = ("==", "!=", ">", "<", ">=", "<=", "in", "contains", "matches")

# Pattern: <ident> <op> <literal>
# operators are matched longest-first so ">=" is not parsed as ">" + "="
_OP_ALT = "|".join(re.escape(op) for op in sorted(_OPS, key=len, reverse=True))
_PAT = re.compile(rf"^\s*([a-zA-Z_][a-zA-Z0-9_\.]*)\s+({_OP_ALT})\s+(.+?)\s*$")


class BranchNode:
    """Evaluate `var op value` conditions. Fixed AST — no eval/exec.

    Implements the `NodeExecutor` Protocol: `execute(config, inputs)`.

    Supported ops: ==, !=, >, <, >=, <=, in, contains, matches.
    Right-hand side literals:
      - numbers (123, 1.5)
      - quoted strings ("foo", 'foo')
      - sets ({a,b,c})
      - bareword (treated as string)
    """

    async def execute(self, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> NodeOutput:
        cond = config.get("condition", "")
        if not isinstance(cond, str) or not cond.strip():
            return NodeOutput(outputs={}, error="BRANCH requires non-empty 'condition'")
        match = _PAT.match(cond)
        if not match:
            return NodeOutput(outputs={}, error=f"BRANCH: cannot parse condition {cond!r}")
        var_name, op, raw_value = match.groups()
        if op not in _OPS:
            return NodeOutput(outputs={}, error=f"BRANCH: unsupported op {op!r}")
        if var_name not in inputs:
            return NodeOutput(outputs={}, error=f"BRANCH: variable {var_name!r} missing")
        actual = inputs[var_name]
        try:
            rhs = _parse_literal(raw_value)
        except ValueError as exc:
            return NodeOutput(outputs={}, error=f"BRANCH: bad literal — {exc}")
        try:
            matched = _eval_op(op, actual, rhs)
        except Exception as exc:  # noqa: BLE001 — surface as NodeOutput.error
            return NodeOutput(outputs={}, error=f"BRANCH: {exc}")
        return NodeOutput(outputs={"matched": matched})


def _parse_literal(raw: str) -> Any:
    raw = raw.strip()
    if raw.startswith("{"):
        if not raw.endswith("}"):
            raise ValueError(f"malformed set literal: {raw!r}")
        items = [p.strip().strip("'\"") for p in raw[1:-1].split(",") if p.strip()]
        return set(items)
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw  # bareword as string


def _eval_op(op: str, lhs: Any, rhs: Any) -> bool:
    if op == "==":
        return lhs == rhs
    if op == "!=":
        return lhs != rhs
    if op in {">", "<", ">=", "<="}:
        return {
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
        }[op](lhs, rhs)
    if op == "in":
        return lhs in rhs
    if op == "contains":
        return rhs in lhs if isinstance(lhs, (list, tuple, set, str)) else False
    if op == "matches":
        if not isinstance(lhs, str):
            return False
        return re.search(rhs, lhs) is not None
    raise ValueError(f"unsupported op {op!r}")

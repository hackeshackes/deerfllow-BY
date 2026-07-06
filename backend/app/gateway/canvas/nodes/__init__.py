"""Workflow canvas node executors — v1.6.x.

Each node type implements the `NodeExecutor` Protocol:

- `prompt` (this file's sibling `prompt.py`) — renders `{{var}}` templates
- `branch` (Task A5) — evaluates fixed `var op value` AST conditions
- `loop` (Task A6) — sentinel for iterate-N execution
- `agent` (Task A6) — delegates to deerflow.client embed
- `tool` (Task A6) — delegates to deerflow.tools.builtins registry

The `WorkflowExecutor` (Task A7) consumes these protocols.
"""

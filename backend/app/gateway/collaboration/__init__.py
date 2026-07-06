"""Cross-workspace thread collaboration (v1.6.x).

Public surface:
- PublishService: orchestrator for publishing a thread into a target workspace
- PublishEvent / PublishResult: value objects for the publish audit trail
- ThreadStore Protocol: duck-typed contract for thread persistence

Router integration (POST /api/threads/{id}/publish) is scaffolded in
``routers/publish.py`` but not wired into ``app.py`` — that lands in the
v1.6.x integration phase.
"""

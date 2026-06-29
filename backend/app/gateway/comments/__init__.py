"""Thread comments domain.

A comment is attached to a thread (or to another comment for a thread of
comments). @mention fan-out reuses the v1.5.5 Subscription subsystem
when present; otherwise mentions are recorded but not delivered.
"""

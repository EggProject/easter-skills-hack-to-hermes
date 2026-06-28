"""Shared constants for the apply + drift pipeline.

Lives in its own module so :mod:`._patcher_pipeline_emit` and other
pipeline siblings can share these strings without inlining them in the
orchestrator. Exit codes, state strings, and failure-reason constants
live in :mod:`._patcher_consts` and are imported directly from there
by consumers.
"""

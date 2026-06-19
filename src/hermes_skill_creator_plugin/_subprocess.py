"""Subprocess helpers for hermes-skill-creator scripts.

Placeholder module kept for plugin discovery; concrete helpers live
in ``tools/subprocess_env.py`` (vendored) and are imported by the
patcher / installer pipelines. Marking the module as non-empty here
suppresses the WPS411 'empty module' finding without re-importing the
vendored helpers into the plugin package surface.
"""

__all__: list[str] = []
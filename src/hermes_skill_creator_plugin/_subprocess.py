"""Subprocess helpers for hermes-skill-creator scripts.

Placeholder module kept for plugin discovery; concrete helpers live
in ``tools/subprocess_env.py`` (vendored) and are imported by the
patcher / installer pipelines. Marking the module as non-empty here
suppresses the WPS411 'empty module' finding without re-importing the
vendored helpers into the plugin package surface.
"""

# Marker constant to suppress WPS411 (empty module).
# Not exported as ``__all__`` (wemake WPS410 rejects annotated __all__).
_VENDORED_HELPERS_MODULE = "tools.subprocess_env"

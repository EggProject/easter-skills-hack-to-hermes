"""tests/stubs — type stubs for host runtime dependencies not installed.

This package provides minimal mypy-visible declarations for modules that
are imported by the plugin source but only exist at the host (Hermes /
Anthropic Claude Code) runtime. They are NEVER imported at runtime by
the plugin; they only satisfy ``mypy --strict``'s import resolution.

Adding a stub here is the correct, type-safe way to address a
``[import-not-found]`` mypy diagnostic for a host-only dep — the
alternative (``# type: ignore``) is forbidden by the project's
no-silencer policy.
"""

"""hermes_skill_creator_plugin — Hermes port of Anthropic's skill-creator.

The plugin package is purely advisory. The migrated skill-creator
lives at skills/skill-creator/ at the worktree root and is installed
flat by Script #2. This package NEVER bundles, contains, or owns the
skill files.

Load model (per `hermes_cli/plugins.py` + plans/03-plugin-spec.md §D1):
the package exposes a single ``register(ctx)`` callable. Hermes invokes
it once at plugin load. The implementation lives in
:mod:`._register`; this ``__init__`` is a pure docstring shim so
``__init__`` itself stays logic-free (wemake WPS412), matching the
codebase's ``i18n/__init__.py`` convention.

Consumption patterns:
    from hermes_skill_creator_plugin._register import register
"""

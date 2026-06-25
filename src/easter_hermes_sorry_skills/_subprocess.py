"""Marker module for plugin discovery (AC-4.6 + AC-4.15).

This file is a non-empty marker so the ``easter_hermes_sorry_skills``
package is importable for plugin discovery. The canonical helper that
strips the nesting-guard env var lives in
``skills/skill-creator/_subprocess.py`` (see
``docs/plans/07-skill-creator-migration.md`` D3 + AC-4.15). The plugin
package must NOT re-implement or re-declare the helper or the guard
constant; doing so would break the single-source-of-truth contract
enforced by ``test_helper_is_single_source_of_truth``.
"""

# Marker constant to suppress WPS411 (empty module).
# Not exported as ``__all__`` (wemake WPS410 rejects annotated __all__).
# Points at the canonical helper's import path used by the migrated
# scripts (``skills/skill-creator/scripts/run_eval.py`` etc.), which
# prepend the skill dir to ``sys.path`` at module load.
_CANONICAL_HELPER_MODULE = "skills.skill_creator._subprocess"

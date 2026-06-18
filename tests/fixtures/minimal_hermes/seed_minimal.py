"""seed_minimal — anchor-contract Hermes home fixture per plans/09-test-strategy.md §Fixture strategy."""

from __future__ import annotations

from pathlib import Path

# Minimal 6-file synthetic Hermes checkout, suitable for migration tests.
MINIMAL_HERMES_FILES: dict[str, str] = {
    "pyproject.toml": "[project]\nname = 'hermes-agent'\nversion = '0.0.0'\n",
    "README.md": "# hermes-agent (synthetic fixture)\n",
    "src/hermes_agent/__init__.py": "",
    "src/hermes_agent/cli.py": "def main() -> None: pass\n",
    "src/hermes_agent/skills.py": "SKILL_CAP = 12\n",
    "skills/.gitkeep": "",
}


def seed_minimal(root: Path) -> Path:
    """Materialize the 6-file synthetic Hermes checkout under `root`. Returns root."""
    for rel, content in MINIMAL_HERMES_FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return root


__all__ = ["MINIMAL_HERMES_FILES", "seed_minimal"]

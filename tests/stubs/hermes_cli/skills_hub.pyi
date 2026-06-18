"""hermes_cli.skills_hub stub — type declarations for the host runtime module."""

from pathlib import Path
from typing import Any

SKILL_FACTORY_SOURCE: str
DEFAULT_SKILL_DIR: Path

def do_install(force: bool, source: str, dest: Path, **kwargs: Any) -> Path: ...

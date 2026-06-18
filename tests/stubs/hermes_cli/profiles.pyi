"""hermes_cli.profiles stub — type declarations for the host runtime module."""

from pathlib import Path
from typing import Any, NamedTuple

class ProfileInfo(NamedTuple):
    name: str
    path: Path
    is_default: bool

def list_profiles() -> list[ProfileInfo]: ...
def get_profile_dir(name: str) -> Path: ...
def profile_config(name: str) -> dict[str, Any]: ...

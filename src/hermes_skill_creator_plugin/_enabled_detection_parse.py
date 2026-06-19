"""src/hermes_skill_creator_plugin/_enabled_detection_parse.py

Frontmatter + YAML parsing helpers for enabled-detection.
"""
from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

import frontmatter
import yaml


_SKILLS_KEY = "skills"
_DISABLED_KEY = "disabled"
_PLATFORMS_KEY = "platforms"
_DISABLED_IF_PLATFORM_KEY = "disabled_if_platform"
_TEXT_ENCODING = "utf-8"
_BAREWORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def parse_frontmatter(path: Path) -> dict[str, Any]:
    """Parse a SKILL.md frontmatter block. Returns {} on any error."""
    try:
        text = path.read_text(encoding=_TEXT_ENCODING)
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    block = text[3:end].strip()
    try:
        post = frontmatter.load(io.StringIO(text))
        if post.metadata:
            return dict(post.metadata)
    except Exception:
        return safe_yaml_dict(block)
    return safe_yaml_dict(block)


def safe_yaml_dict(block: str) -> dict[str, Any]:
    """Parse a YAML block; return {} on any failure or non-dict result."""
    try:
        loaded = yaml.safe_load(block)
    except yaml.YAMLError:
        return {}
    return dict(loaded) if isinstance(loaded, dict) else {}


def load_config(profile_path: Path) -> dict[str, Any]:
    """Read ``<profile_path>/config.yaml``. Returns {} on missing."""
    cfg = profile_path / "config.yaml"
    if not cfg.is_file():
        return {}
    try:
        text = cfg.read_text(encoding=_TEXT_ENCODING)
    except OSError:
        return {}
    return safe_yaml_dict(text)


def add_list_entries(source: Any, target: set[str]) -> None:
    """Populate ``target`` from list or bareword scalar ``source``."""
    if isinstance(source, list):
        for entry in source:
            target.add(str(entry))
    elif isinstance(source, str) and _BAREWORD_RE.fullmatch(source):
        target.add(source)

"""AuditReport dataclass for cli_profiles (Script #2 per-profile audit/flip).

TDD tests reference ``hermes_skill_creator_plugin.cli_profiles.AuditReport``;
the original class is re-exported from ``cli_profiles.py`` so existing
imports continue to work.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass(frozen=True)
class AuditReport:
    """A deterministic per-profile audit/flip report.

    The dataclass serializes to JSON via ``to_json_bytes()``; the
    serialized form is byte-identical across runs given the same
    inputs and a stable ``generated_at``.

    The class is dict-like (``report["profiles"]``) for ergonomic
    tests; ``to_dict()`` returns the canonical shape.
    """

    tool: str
    version: str
    generated_at: str
    profiles: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return the dict shape, sorting the profiles by ``profile_name`` (D7)."""
        return {
            "tool": self.tool,
            "version": self.version,
            "generated_at": self.generated_at,
            "profiles": sorted(
                self.profiles,
                key=lambda report_row: report_row["profile_name"],
            ),
        }

    def to_json_bytes(self) -> bytes:
        """Serialize ``to_dict()`` deterministically (sorted keys + compact)."""
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def __contains__(self, key: str) -> bool:
        return key in self.to_dict()

    def __hash__(self) -> int:
        # Hash on a frozen view of to_dict(); lists are not hashable so
        # we freeze the profiles list into a tuple of tuples.
        d = self.to_dict()
        return hash(
            (
                d["tool"],
                d["version"],
                d["generated_at"],
                tuple(tuple(sorted(report_row.items())) for report_row in d["profiles"]),
            )
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AuditReport):
            return self.to_dict() == other.to_dict()
        if isinstance(other, dict):
            return self.to_dict() == other
        return NotImplemented

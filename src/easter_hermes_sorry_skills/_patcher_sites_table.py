"""Idempotent Hermes patcher — S1.cap (MAX_DESCRIPTION_LENGTH cap-raise).

The patcher has exactly one site: ``S1_CAP_SITE``. It replaces the
hard-coded ``60`` cap in ``agent/skill_utils.py``'s ``extract_skill_description``
with a constant-based cap (``MAX_DESCRIPTION_LENGTH``) so the operator
can tune the cap without code changes.

Defines the ``Anchor`` and ``Site`` dataclasses used by the patcher
pipeline (``mutate_lines_for_site``).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

# --- file layout constants -----------------------------------------------
TOOLS_SKILL_UTILS_REL = Path("agent") / "skill_utils.py"

# --- site ``kind`` constants (WPS226 — reused > 3 times) -------------------
KIND_APPEND = "append"
KIND_CAP = "cap"


# --- site data classes ----------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Anchor:
    """A single physical line that the patcher must locate exactly.

    ``line`` is 1-based; ``text`` is the byte-exact physical line
    content (no implicit-concat normalization, no whitespace scrubbing).
    """

    line: int
    text: str


@dataclasses.dataclass(frozen=True)
class Site:
    """A patch site.

    A site is identified by ``site_id`` and a list of :class:`Anchor`
    entries (1 anchor for an append-only Task E site, 2 anchors for
    the S1.cap atomic pair).

    ``kind`` is ``"cap"`` (replace pair), ``"append"`` (additive Task
    E line, ADDITIVE-ONLY per plans/05 B1.0), or ``"schema_append"``
    (E6-style: append a line inside a multi-line string value).

    ``file`` is the path RELATIVE to the --target root.

    ``expected_replacement`` is the verbatim text that, when present at
    the site, means the site is ALREADY patched (idempotency check).
    """

    site_id: str
    file_path: Path
    anchors: tuple[Anchor, ...]
    insertion: str
    expected_replacement: str
    kind: str = KIND_APPEND
    line_for_state: int = 0  # primary anchor line for sidecar / migration note

    def primary_anchor(self) -> Anchor:
        return self.anchors[0]


# --- canonical line-number constants (plans/04 §Multi-signal) -------------
S1_CAP_LINE_A = 688
S1_CAP_LINE_B = 689

# --- the S1.cap site (two-anchor atomic pair) -----------------------------

S1_CAP_SITE = Site(
    site_id="S1.cap",
    file_path=TOOLS_SKILL_UTILS_REL,
    anchors=(
        Anchor(line=S1_CAP_LINE_A, text="    if len(desc) > 60:"),
        Anchor(line=S1_CAP_LINE_B, text='        return desc[:57] + "..."'),
    ),
    insertion=(
        '    if len(desc) > MAX_DESCRIPTION_LENGTH:\n        return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."\n'
    ),
    # The idempotency check looks for the replacement text:
    expected_replacement=(
        '    if len(desc) > MAX_DESCRIPTION_LENGTH:\n        return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."\n'
    ),
    kind=KIND_CAP,
    line_for_state=S1_CAP_LINE_A,
)

# AC-2.11 fallback: when ``tools.skills_tool`` cannot be imported in
# the target checkout (potential circular import), the patcher swaps
# S1.cap for S1.cap_fallback, which uses a LOCAL constant
# ``_MAX_DESCRIPTION_LENGTH = 1024`` instead of the cross-module
# ``MAX_DESCRIPTION_LENGTH``. The anchors are identical to S1.cap so
# the multi-signal targeting lines up; only the replacement text
# differs (it prepends a local-definition line).
_FALLBACK_MAX_DESCRIPTION_LENGTH = 1024
S1_CAP_SITE_FALLBACK = Site(
    site_id="S1.cap_fallback",
    file_path=TOOLS_SKILL_UTILS_REL,
    anchors=(
        Anchor(line=S1_CAP_LINE_A, text="    if len(desc) > 60:"),
        Anchor(line=S1_CAP_LINE_B, text='        return desc[:57] + "..."'),
    ),
    insertion=(
        f"    _MAX_DESCRIPTION_LENGTH = {_FALLBACK_MAX_DESCRIPTION_LENGTH}\n"
        "    if len(desc) > _MAX_DESCRIPTION_LENGTH:\n"
        '        return desc[:_MAX_DESCRIPTION_LENGTH - 3] + "..."\n'
    ),
    expected_replacement=(
        f"    _MAX_DESCRIPTION_LENGTH = {_FALLBACK_MAX_DESCRIPTION_LENGTH}\n"
        "    if len(desc) > _MAX_DESCRIPTION_LENGTH:\n"
        '        return desc[:_MAX_DESCRIPTION_LENGTH - 3] + "..."\n'
    ),
    kind=KIND_CAP,
    line_for_state=S1_CAP_LINE_A,
)

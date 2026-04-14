"""Shared IMDb award-string ceremony extraction (used by award_show_counts, actor_year_award_matrix)."""

import re

# Text before " — YYYY Winner|Nominee " in IMDb award lines.
CEREMONY_PATTERN = r"^(.+?) — \d{4} (?:Winner|Nominee) "

CEREMONY_RE = re.compile(CEREMONY_PATTERN)


def parse_ceremony(award: str) -> str | None:
    """Return the ceremony name (group 1) or None if the string does not match."""
    m = CEREMONY_RE.match((award or "").strip())
    return m.group(1) if m else None

"""
Map IMDb ceremony name (award_show) to a fixed group_key for aggregated columns.
Major ceremonies are handled separately in actor_year_award_matrix; this classifies the rest.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

# Stable column order for group_* noms/wins pairs.
GROUP_KEYS: tuple[str, ...] = (
    "prediction_online",
    "us_regional_critics",
    "national_critics",
    "international_film",
    "major_festival",
    "television",
    "audience_pop",
    "genre",
    "voice_or_animation",
    "negative",
    "other",
)


def load_group_overrides(path: str | Path) -> dict[str, str]:
    """Load award_show -> group_key from CSV (skips blank rows and #-comments in award_show)."""
    p = Path(path)
    if not p.is_file():
        return {}
    out: dict[str, str] = {}
    with p.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "award_show" not in reader.fieldnames or "group_key" not in reader.fieldnames:
            return {}
        for row in reader:
            k = (row.get("award_show") or "").strip()
            v = (row.get("group_key") or "").strip()
            if not k or k.startswith("#") or not v:
                continue
            out[k] = v
    return out


def _has_any(hay: str, needles: tuple[str, ...]) -> bool:
    sl = hay.lower()
    return any(n in sl for n in needles)


def classify_group(award_show: str, overrides: dict[str, str] | None = None) -> str:
    """
    Return group_key for a non-major ceremony. First check overrides; then heuristic rules.
    """
    o = overrides or {}
    if award_show in o:
        g = o[award_show]
        if g in GROUP_KEYS:
            return g
        return "other"

    s = award_show
    sl = s.lower()

    # negative
    if _has_any(s, ("razzie", "stinkers bad movie", "the stinkers")):
        return "negative"

    # voice / animation casting
    if "behind the voice actors" in sl:
        return "voice_or_animation"

    # television (broad)
    if _has_any(
        s,
        (
            "emmy",
            "daytime emmy",
            "primetime emmy",
            "television",
            " tv ",
            "tv awards",
            "critics choice television",
            "children's and family emmy",
        ),
    ):
        return "television"

    # genre / horror-sci
    if _has_any(
        s,
        (
            "science fiction, fantasy",
            "saturn award",
            "fangoria",
            "chainsaw award",
            "scream awards",
            "chlotrudis",
            "horror",
        ),
    ):
        return "genre"

    # major film festivals (named events; long tail "* Film Festival" below)
    if _has_any(
        s,
        (
            "cannes film festival",
            "venice film festival",
            "berlin international film festival",
            "sundance",
            "toronto international film festival",
            "palm springs international film festival",
            "santa barbara international film festival",
            "sxsw",
            "tribeca",
        ),
    ):
        return "major_festival"
    if "international film festival" in sl and "critics" not in sl:
        return "major_festival"
    if sl.endswith("film festival") and "critics" not in sl:
        return "major_festival"

    # national-level critics (before generic "online" prediction bucket)
    if _has_any(
        s,
        (
            "national society of film critics",
            "national board of review",
            "new york film critics circle",
            "los angeles film critics association",
            "boston society of film critics",
            "london critics circle film",
            "washington dc area film critics",
            "online film critics society awards",
        ),
    ):
        return "national_critics"

    # prediction / online communities & polls
    if _has_any(
        s,
        (
            "gold derby",
            "awards circuit",
            "online film & television association",
            "international online cinema awards",
            "inoca",
            "indiewire critics",
            "golden schmoes",
            "village voice film poll",
            "cineuphoria awards",
        ),
    ):
        return "prediction_online"

    # US regional critics associations (city / state)
    if (
        "film critics association" in sl
        or "film critics society" in sl
        or "film critics circle" in sl
        or re.search(
            r"\b(chicago|san diego|dallas|houston|seattle|denver|austin|detroit|"
            r"las vegas|phoenix|kansas city|florida|georgia|north carolina|utah|"
            r"oklahoma|hawaii|philadelphia|atlanta|minnesota|iowa|indiana)\b.*critics",
            sl,
        )
        or "critics association awards" in sl
    ):
        if "national society" not in sl and "national board" not in sl:
            return "us_regional_critics"

    # international (non-US) film prizes & academies
    if _has_any(
        s,
        (
            "european film awards",
            "césar awards",
            "cesar awards",
            "australian academy of cinema",
            "aacta",
            "irish film and television",
            "british independent film",
            "canadian screen awards",
            "empire awards, uk",
            "national film awards, uk",
            "evening standard british film",
            "australian film institute",
        ),
    ):
        return "international_film"

    # audience / pop culture / music / general popularity
    if _has_any(
        s,
        (
            "teen choice",
            "people's choice awards",
            "kids' choice",
            "mtv ",
            "bet awards",
            "image awards (naacp)",
            "grammy awards",
            "young artist awards",
            "blockbuster entertainment awards",
        ),
    ):
        return "audience_pop"

    return "other"


def slugify_award_show(award_show: str, prefix: str, used: set[str]) -> str:
    """Stable slug for CSV column names; prefix e.g. maj_ or grp_."""
    base = re.sub(r"[^a-z0-9]+", "_", award_show.lower()).strip("_")
    if not base:
        base = "x"
    base = base[:80]
    cand = f"{prefix}{base}"
    n = 2
    while cand in used:
        cand = f"{prefix}{base}_{n}"
        n += 1
    used.add(cand)
    return cand

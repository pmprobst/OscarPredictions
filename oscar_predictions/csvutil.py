"""Shared CSV helpers (parity-preserving utilities for pipeline scripts)."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path
from typing import TextIO

from oscar_predictions.oscar_scrape import nm_id_from_profile_url


def missing_required_columns(fieldnames: Iterable[str] | None, required: set[str]) -> list[str]:
    """Return sorted list of required column names absent from fieldnames."""
    fn = {c.strip() for c in (fieldnames or [])}
    return sorted(required - fn)


def open_append_csv_writer(
    path: str | Path,
    fieldnames: list[str],
) -> tuple[TextIO, csv.DictWriter]:
    """
    Open path for append; return (file, DictWriter). Write header if file is empty.
    Caller must close the file.
    """
    p = Path(path)
    f = p.open("a", newline="", encoding="utf-8")
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    if f.tell() == 0:
        writer.writeheader()
    return f, writer


def load_nm_ids_from_actor_url_column(csv_path: str | Path, *, column: str = "actor_imdb_url") -> set[str]:
    """Unique IMDb nm ids from rows in a CSV with an actor profile URL column."""
    p = Path(csv_path)
    if not p.is_file():
        return set()
    out: set[str] = set()
    with p.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = (row.get(column) or "").strip()
            nm = nm_id_from_profile_url(url)
            if nm:
                out.add(nm)
    return out

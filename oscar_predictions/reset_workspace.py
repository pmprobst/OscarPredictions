"""Trim workspace base CSVs to a cutoff year, prune no_award actors, clear derived outputs."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from oscar_predictions.workspace import DataWorkspace


def _parse_year(value: str | None) -> int | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _atomic_replace_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for row in rows:
                w.writerow({k: row.get(k, "") for k in fieldnames})
        tmp.replace(path)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


def _trim_csv_by_year(
    path: Path,
    *,
    cutoff_year: int,
    dry_run: bool,
) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "total_rows": 0,
            "kept_rows": 0,
            "skipped_bad_year": 0,
            "written": False,
        }

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames or "year" not in fieldnames:
            return {
                "path": str(path),
                "exists": True,
                "error": "missing year column or header",
                "total_rows": 0,
                "kept_rows": 0,
                "skipped_bad_year": 0,
                "written": False,
            }
        raw_rows = list(reader)

    total = len(raw_rows)
    kept: list[dict[str, str]] = []
    skipped_bad = 0
    for row in raw_rows:
        y = _parse_year(row.get("year"))
        if y is None:
            skipped_bad += 1
            continue
        if y <= cutoff_year:
            kept.append(row)
        # else dropped (post-cutoff)

    if not dry_run:
        _atomic_replace_csv(path, list(fieldnames), kept)

    return {
        "path": str(path),
        "exists": True,
        "total_rows": total,
        "kept_rows": len(kept),
        "skipped_bad_year": skipped_bad,
        "written": not dry_run,
    }


def _collect_actor_urls(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "actor_imdb_url" not in reader.fieldnames:
            return set()
        return {str(row.get("actor_imdb_url") or "").strip() for row in reader if row.get("actor_imdb_url")}


def _prune_no_award_actors(
    path: Path,
    *,
    universe_urls: set[str],
    dry_run: bool,
) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "total_rows": 0,
            "kept_rows": 0,
            "written": False,
        }

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames or "actor_imdb_url" not in fieldnames:
            return {
                "path": str(path),
                "exists": True,
                "error": "missing actor_imdb_url column or header",
                "total_rows": 0,
                "kept_rows": 0,
                "written": False,
            }
        raw_rows = list(reader)

    total = len(raw_rows)
    kept = [row for row in raw_rows if str(row.get("actor_imdb_url") or "").strip() in universe_urls]

    if not dry_run:
        _atomic_replace_csv(path, list(fieldnames), kept)

    return {
        "path": str(path),
        "exists": True,
        "total_rows": total,
        "kept_rows": len(kept),
        "written": not dry_run,
    }


def run_reset_workspace(
    workspace: DataWorkspace,
    *,
    cutoff_year: int = 2023,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Trim year-bearing base CSVs to cutoff_year, prune no_award_actors to the remaining
    cast/award graph, delete derived outputs, and remove sync state.
    """
    movies_stats = _trim_csv_by_year(workspace.movies, cutoff_year=cutoff_year, dry_run=dry_run)
    cast_stats = _trim_csv_by_year(workspace.cast, cutoff_year=cutoff_year, dry_run=dry_run)
    awards_stats = _trim_csv_by_year(workspace.actor_awards, cutoff_year=cutoff_year, dry_run=dry_run)

    no_award_stats: dict[str, Any]
    if workspace.cast.exists() or workspace.actor_awards.exists():
        if dry_run:
            universe: set[str] = set()
            for p in (workspace.cast, workspace.actor_awards):
                if not p.exists():
                    continue
                with p.open(newline="", encoding="utf-8") as f:
                    r = csv.DictReader(f)
                    if not r.fieldnames or "year" not in r.fieldnames or "actor_imdb_url" not in r.fieldnames:
                        continue
                    for row in r:
                        y = _parse_year(row.get("year"))
                        if y is not None and y <= cutoff_year:
                            u = str(row.get("actor_imdb_url") or "").strip()
                            if u:
                                universe.add(u)
        else:
            universe = _collect_actor_urls(workspace.cast) | _collect_actor_urls(workspace.actor_awards)
        no_award_stats = _prune_no_award_actors(
            workspace.no_award_actors,
            universe_urls=universe,
            dry_run=dry_run,
        )
    else:
        no_award_stats = {
            "path": str(workspace.no_award_actors),
            "skipped": True,
            "reason": "film_actors.csv and actor_awards.csv both missing",
        }

    if dry_run:
        derived_removed: list[str] = []
        for p in (
            workspace.actor_year_matrix,
            workspace.film_actor_totals,
            workspace.movie_totals,
            workspace.award_show_counts,
        ):
            if p.exists():
                derived_removed.append(str(p))
        state_removed = workspace.state_file.exists()
    else:
        derived_removed = workspace.delete_derived_outputs()
        state_removed = False
        if workspace.state_file.exists():
            workspace.state_file.unlink()
            state_removed = True

    return {
        "dry_run": dry_run,
        "cutoff_year": cutoff_year,
        "workspace": str(workspace.root),
        "movies": movies_stats,
        "film_actors": cast_stats,
        "actor_awards": awards_stats,
        "no_award_actors": no_award_stats,
        "derived_removed": derived_removed,
        "state_removed": state_removed,
    }

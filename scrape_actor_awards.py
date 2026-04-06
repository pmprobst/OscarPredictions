#!/usr/bin/env python3
"""
Read unique actors from a film–actor CSV (e.g. film_actors.csv) and append rows to
actor_awards.csv with each person's full IMDb awards history (nominations and wins).

Actors whose nm id already appears in the output awards CSV are skipped unless
--force-rescrape is used.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from playwright.sync_api import sync_playwright

from oscar_scrape import (
    ACTOR_AWARD_FIELDNAMES,
    ACTOR_AWARDS_CSV_FILE,
    CAST_CSV_FILE,
    _imdb_browser_context,
    extract_person_award_rows,
    nm_id_from_profile_url,
)


def _load_unique_actors(input_path: str) -> list[tuple[str, str]]:
    """
    Return ordered list of (actor_name, actor_imdb_url), first occurrence wins per nm id.
    """
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = (row.get("actor_imdb_url") or "").strip()
            name = (row.get("actor_name") or "").strip()
            nm = nm_id_from_profile_url(url)
            if not nm or nm in seen:
                continue
            seen.add(nm)
            out.append((name, url if url.startswith("http") else f"https://www.imdb.com/name/{nm}/"))
    return out


def _load_existing_nm_ids(output_path: str) -> set[str]:
    """Unique IMDb nm ids already present in the awards CSV."""
    p = Path(output_path)
    if not p.is_file():
        return set()
    out: set[str] = set()
    with p.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = (row.get("actor_imdb_url") or "").strip()
            nm = nm_id_from_profile_url(url)
            if nm:
                out.add(nm)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape IMDb awards pages for each unique actor in a film_actors-style CSV."
    )
    parser.add_argument(
        "--input",
        default=CAST_CSV_FILE,
        help=f"Input CSV with actor_name, actor_imdb_url (default: {CAST_CSV_FILE}).",
    )
    parser.add_argument(
        "--output",
        default=ACTOR_AWARDS_CSV_FILE,
        help=f"Output CSV path (default: {ACTOR_AWARDS_CSV_FILE}). Also used to skip actors already listed.",
    )
    parser.add_argument(
        "--force-rescrape",
        action="store_true",
        help="Scrape every unique cast actor even if already present in --output (may duplicate rows).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium without opening a window.",
    )
    parser.add_argument(
        "--max-actors",
        type=int,
        default=None,
        metavar="N",
        help="After skip filter, process at most N actors (for testing).",
    )
    args = parser.parse_args()

    actors = _load_unique_actors(args.input)
    total_unique = len(actors)

    if args.force_rescrape:
        print(f"Force rescrape: processing up to {total_unique} unique actors from cast list.")
    else:
        existing_nm = _load_existing_nm_ids(args.output)
        before = len(actors)
        actors = [
            (n, u)
            for n, u in actors
            if nm_id_from_profile_url(u) not in existing_nm
        ]
        skipped = before - len(actors)
        print(
            f"Skipped {skipped} actors already in {args.output}; "
            f"{len(actors)} to scrape (of {total_unique} unique in cast CSV)."
        )

    if args.max_actors is not None:
        actors = actors[: args.max_actors]

    out_path = args.output
    with open(out_path, "a", newline="", encoding="utf-8") as outf:
        writer = csv.DictWriter(outf, fieldnames=ACTOR_AWARD_FIELDNAMES)
        if outf.tell() == 0:
            writer.writeheader()

        with sync_playwright() as p:
            browser, context = _imdb_browser_context(p, args.headless)
            try:
                for idx, (name, url) in enumerate(actors, start=1):
                    print(f"[{idx}/{len(actors)}] {name}")
                    try:
                        rows = extract_person_award_rows(context, url, name)
                        for row in rows:
                            writer.writerow(row)
                        outf.flush()
                    except Exception as e:
                        print(f"  Error: {e}")
            finally:
                context.close()
                browser.close()

    print(f"Award rows written incrementally to {out_path}")


if __name__ == "__main__":
    main()

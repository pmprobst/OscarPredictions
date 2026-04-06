#!/usr/bin/env python3
"""
Read unique actors from a film–actor CSV (e.g. film_actors.csv) and append rows to
actor_awards.csv with each person's full IMDb awards history (nominations and wins).

Actors whose nm id already appears in the awards CSV are skipped unless
--force-rescrape is used. The CSV only gains rows when IMDb lists at least one
award/nomination line for that person.

Actors scraped successfully with no matching award lines are appended to
no_award_actors.csv (actor_name, actor_imdb_url). Their nm ids are skipped on
later runs like actors already present in actor_awards.csv.
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
    NO_AWARD_ACTORS_CSV_FILE,
    NO_AWARD_ACTORS_FIELDNAMES,
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


def _load_existing_nm_ids(csv_path: str) -> set[str]:
    """Unique IMDb nm ids already present in a CSV with actor_imdb_url column."""
    p = Path(csv_path)
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
        "--no-award-output",
        default=NO_AWARD_ACTORS_CSV_FILE,
        dest="no_award_output",
        help=f"CSV for actors with no listed award lines after a successful scrape (default: {NO_AWARD_ACTORS_CSV_FILE}). Used to skip them on later runs.",
    )
    parser.add_argument(
        "--force-rescrape",
        action="store_true",
        help="Scrape every unique cast actor; ignore both --output and --no-award-output for skipping (may duplicate award rows).",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Open a visible Chromium window (default: headless, no window).",
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
        existing_award_nm = _load_existing_nm_ids(args.output)
        existing_no_award_nm = _load_existing_nm_ids(args.no_award_output)
        cast_actors = actors
        before = len(cast_actors)
        skipped_in_awards = sum(
            1 for n, u in cast_actors if nm_id_from_profile_url(u) in existing_award_nm
        )
        skipped_in_no_award = sum(
            1
            for n, u in cast_actors
            if nm_id_from_profile_url(u) in existing_no_award_nm
            and nm_id_from_profile_url(u) not in existing_award_nm
        )
        actors = [
            (n, u)
            for n, u in cast_actors
            if nm_id_from_profile_url(u) not in existing_award_nm
            and nm_id_from_profile_url(u) not in existing_no_award_nm
        ]
        skipped = before - len(actors)
        print(
            f"Skipped {skipped} unique cast actors ({skipped_in_awards} with award rows in {args.output}, "
            f"{skipped_in_no_award} listed as no awards in {args.no_award_output}); "
            f"{len(actors)} to scrape (of {total_unique} unique in cast CSV)."
        )

    if args.max_actors is not None:
        actors = actors[: args.max_actors]

    if not actors:
        print("No actors to scrape; exiting.")
        return

    out_path = args.output
    no_award_path = args.no_award_output
    with open(out_path, "a", newline="", encoding="utf-8") as outf, open(
        no_award_path, "a", newline="", encoding="utf-8"
    ) as no_award_f:
        writer = csv.DictWriter(outf, fieldnames=ACTOR_AWARD_FIELDNAMES)
        if outf.tell() == 0:
            writer.writeheader()

        no_award_writer = csv.DictWriter(no_award_f, fieldnames=NO_AWARD_ACTORS_FIELDNAMES)
        if no_award_f.tell() == 0:
            no_award_writer.writeheader()

        with sync_playwright() as p:
            browser, context = _imdb_browser_context(p, headless=not args.headed)
            try:
                for idx, (name, url) in enumerate(actors, start=1):
                    print(f"[{idx}/{len(actors)}] {name}")
                    try:
                        result = extract_person_award_rows(context, url, name)
                        if result.ok:
                            if result.rows:
                                for row in result.rows:
                                    writer.writerow(row)
                            else:
                                nm = nm_id_from_profile_url(url)
                                canonical = (
                                    f"https://www.imdb.com/name/{nm}/"
                                    if nm
                                    else (url if url.startswith("http") else url)
                                )
                                no_award_writer.writerow(
                                    {"actor_name": name, "actor_imdb_url": canonical}
                                )
                                no_award_f.flush()
                            outf.flush()
                        else:
                            print("  Scrape failed (not recording in no-award list).")
                    except Exception as e:
                        print(f"  Error: {e}")
            finally:
                context.close()
                browser.close()

    print(f"Award rows written incrementally to {out_path}; no-award actors appended to {no_award_path}")


if __name__ == "__main__":
    main()

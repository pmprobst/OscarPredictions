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
from typing import Sequence

from oscar_predictions.cliutil import (
    add_browser_args_default_headless,
    resolve_headless_default_headless,
)
from oscar_predictions.csvutil import open_append_csv_writer, load_nm_ids_from_actor_url_column
from oscar_predictions.oscar_scrape import (
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


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
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
    add_browser_args_default_headless(parser)
    parser.add_argument(
        "--max-actors",
        type=int,
        default=None,
        metavar="N",
        help="After skip filter, process at most N actors (for testing).",
    )
    return parser.parse_args(argv)


def run_scrape_actor_awards(
    *,
    input_path: str = CAST_CSV_FILE,
    output_path: str = ACTOR_AWARDS_CSV_FILE,
    no_award_output: str = NO_AWARD_ACTORS_CSV_FILE,
    force_rescrape: bool = False,
    force_recheck_nm_ids: set[str] | None = None,
    headless: bool = True,
    max_actors: int | None = None,
) -> dict[str, int | str]:
    actors = _load_unique_actors(input_path)
    total_unique = len(actors)

    if force_rescrape:
        print(f"Force rescrape: processing up to {total_unique} unique actors from cast list.")
    else:
        forced_nm_ids = force_recheck_nm_ids or set()
        existing_award_nm = load_nm_ids_from_actor_url_column(output_path)
        existing_no_award_nm = load_nm_ids_from_actor_url_column(no_award_output)
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
            and (
                nm_id_from_profile_url(u) not in existing_no_award_nm
                or nm_id_from_profile_url(u) in forced_nm_ids
            )
        ]
        skipped = before - len(actors)
        print(
            f"Skipped {skipped} unique cast actors ({skipped_in_awards} with award rows in {output_path}, "
            f"{skipped_in_no_award} listed as no awards in {no_award_output}); "
            f"{len(actors)} to scrape (of {total_unique} unique in cast CSV)."
        )

    if max_actors is not None:
        actors = actors[:max_actors]

    if not actors:
        print("No actors to scrape; exiting.")
        return {
            "rows_added": 0,
            "award_rows_added": 0,
            "no_award_rows_added": 0,
            "actors_targeted": 0,
            "output_awards": output_path,
            "output_no_award": no_award_output,
        }

    outf, writer = open_append_csv_writer(output_path, ACTOR_AWARD_FIELDNAMES)
    no_award_f, no_award_writer = open_append_csv_writer(
        no_award_output, NO_AWARD_ACTORS_FIELDNAMES
    )
    award_rows_added = 0
    no_award_rows_added = 0
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser, context = _imdb_browser_context(p, headless=headless)
            try:
                for idx, (name, url) in enumerate(actors, start=1):
                    print(f"[{idx}/{len(actors)}] {name}")
                    try:
                        result = extract_person_award_rows(context, url, name)
                        if result.ok:
                            if result.rows:
                                for row in result.rows:
                                    writer.writerow(row)
                                    award_rows_added += 1
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
                                no_award_rows_added += 1
                                no_award_f.flush()
                            outf.flush()
                        else:
                            print("  Scrape failed (not recording in no-award list).")
                    except Exception as e:
                        print(f"  Error: {e}")
            finally:
                context.close()
                browser.close()
    finally:
        outf.close()
        no_award_f.close()

    print(
        f"Award rows written incrementally to {output_path}; no-award actors appended to {no_award_output}"
    )
    return {
        "rows_added": award_rows_added + no_award_rows_added,
        "award_rows_added": award_rows_added,
        "no_award_rows_added": no_award_rows_added,
        "actors_targeted": len(actors),
        "output_awards": output_path,
        "output_no_award": no_award_output,
    }


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    run_scrape_actor_awards(
        input_path=args.input,
        output_path=args.output,
        no_award_output=args.no_award_output,
        force_rescrape=args.force_rescrape,
        headless=resolve_headless_default_headless(args),
        max_actors=args.max_actors,
    )


if __name__ == "__main__":
    main()

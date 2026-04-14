#!/usr/bin/env python3
"""Scrape IMDb full-credits cast for rows in movies.csv (Best Picture list from scrape_movies).

For each newly scraped film, removes that cast's nm ids from no_award_actors.csv (unless
--skip-no-award-prune) so scrape_actor_awards.py can recheck them for new IMDb award lines.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Sequence

from oscar_predictions.cliutil import (
    add_browser_args_default_headless,
    resolve_headless_default_headless,
)
from oscar_predictions.csvutil import missing_required_columns, open_append_csv_writer
from oscar_predictions.oscar_scrape import (
    CAST_CSV_FILE,
    CSV_FILE,
    CAST_FIELDNAMES,
    NO_AWARD_ACTORS_CSV_FILE,
    _imdb_browser_context,
    extract_film_actor_rows,
    nm_id_from_profile_url,
    remove_nm_ids_from_no_award_csv,
)


def _load_existing_film_keys(path: str) -> set[tuple[str, str]]:
    """
    (year_str, film_title) pairs already in the cast CSV, for skip logic.
    year_str is normalized with str(int(...)) to match scrape output.
    """
    p = Path(path)
    if not p.is_file():
        return set()
    out: set[tuple[str, str]] = set()
    with p.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_y = (row.get("year") or "").strip()
            try:
                y = int(raw_y)
            except ValueError:
                continue
            title = (row.get("film_title") or "").strip()
            out.add((str(y), title))
    return out


def _load_movies_rows(movies_path: Path) -> list[dict[str, str]]:
    with movies_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit(f"No header row in {movies_path}")
        required = {"title", "url", "year"}
        miss = missing_required_columns(reader.fieldnames, required)
        if miss:
            raise SystemExit(f"{movies_path} missing columns: {miss}")
        return list(reader)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape IMDb full credits for each film in movies.csv (title, url, year); "
            "append cast rows to film_actors.csv unless that year/title is already present."
        )
    )
    parser.add_argument(
        "--movies",
        default=CSV_FILE,
        help=f"Input CSV from scrape_movies.py (default: {CSV_FILE}).",
    )
    parser.add_argument(
        "--year",
        type=int,
        metavar="Y",
        help="Only process movies.csv rows with this ceremony year (optional).",
    )
    add_browser_args_default_headless(parser)
    parser.add_argument(
        "--csv-cast",
        default=CAST_CSV_FILE,
        help=f"Film–actor CSV path (default: {CAST_CSV_FILE}).",
    )
    parser.add_argument(
        "--max-movies",
        type=int,
        default=None,
        metavar="N",
        help="Scrape at most N films not already in film_actors (after --year filter).",
    )
    parser.add_argument(
        "--no-award-csv",
        default=NO_AWARD_ACTORS_CSV_FILE,
        dest="no_award_csv",
        help=(
            f"No-award registry CSV (default: {NO_AWARD_ACTORS_CSV_FILE}). "
            "Cast nm ids from newly scraped films are removed so scrape_actor_awards can recheck."
        ),
    )
    parser.add_argument(
        "--skip-no-award-prune",
        action="store_true",
        help="Do not remove cast nm ids from the no-award CSV after scraping new films.",
    )
    return parser.parse_args(argv)


def run_scrape_actors(
    *,
    movies: str | Path = CSV_FILE,
    year: int | None = None,
    headless: bool = True,
    csv_cast: str = CAST_CSV_FILE,
    max_movies: int | None = None,
    no_award_csv: str = NO_AWARD_ACTORS_CSV_FILE,
    skip_no_award_prune: bool = False,
) -> dict[str, int | str]:
    movies_path = Path(movies)
    if not movies_path.is_file():
        raise SystemExit(f"Movies file not found: {movies_path}")

    try:
        rows = _load_movies_rows(movies_path)
    except OSError as e:
        raise SystemExit(f"Cannot read {movies_path}: {e}") from e

    cast_path = csv_cast
    existing_films = _load_existing_film_keys(cast_path)

    cf, cast_writer = open_append_csv_writer(cast_path, CAST_FIELDNAMES)
    rows_added = 0
    scraped_films = 0
    removed_no_award_rows = 0
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser, context = _imdb_browser_context(p, headless=headless)
            try:
                scrape_attempts = 0
                for row in rows:
                    raw_title = (row.get("title") or "").strip()
                    url = (row.get("url") or "").strip()
                    raw_y = (row.get("year") or "").strip()
                    try:
                        y = int(raw_y)
                    except ValueError:
                        print(f"Skip (invalid year): {raw_title!r} year={raw_y!r}", file=sys.stderr)
                        continue

                    if year is not None and y != year:
                        continue

                    if not url:
                        print(f"Skip (empty url): {raw_title} ({y})", file=sys.stderr)
                        continue

                    key = (str(y), raw_title)
                    if key in existing_films:
                        print(f"Skip (already in cast CSV): {raw_title} ({y})")
                        continue

                    if max_movies is not None and scrape_attempts >= max_movies:
                        break

                    scrape_attempts += 1
                    try:
                        print(f"Cast: {raw_title} ({y})")
                        rows_written = 0
                        nms_this_film: set[str] = set()
                        for cast_row in extract_film_actor_rows(
                            context, url, y, raw_title
                        ):
                            cast_writer.writerow(cast_row)
                            rows_written += 1
                            nm = nm_id_from_profile_url(
                                (cast_row.get("actor_imdb_url") or "").strip()
                            )
                            if nm:
                                nms_this_film.add(nm)
                        cf.flush()
                        if rows_written:
                            existing_films.add(key)
                            rows_added += rows_written
                            scraped_films += 1
                            if not skip_no_award_prune:
                                removed = remove_nm_ids_from_no_award_csv(
                                    no_award_csv, nms_this_film
                                )
                                removed_no_award_rows += removed
                                if removed:
                                    print(
                                        f"Removed {removed} row(s) from {no_award_csv} "
                                        "(recheck awards for cast of new film)."
                                    )
                    except Exception as e:
                        print(f"Error scraping {raw_title} ({y}): {e}", file=sys.stderr)
            finally:
                context.close()
                browser.close()
    finally:
        cf.close()

    print(f"Film–actor pairs written incrementally to {cast_path}")
    return {
        "rows_added": rows_added,
        "cast_rows_added": rows_added,
        "scraped_films": scraped_films,
        "no_award_rows_removed": removed_no_award_rows,
        "output_cast": cast_path,
    }


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    run_scrape_actors(
        movies=args.movies,
        year=args.year,
        headless=resolve_headless_default_headless(args),
        csv_cast=args.csv_cast,
        max_movies=args.max_movies,
        no_award_csv=args.no_award_csv,
        skip_no_award_prune=args.skip_no_award_prune,
    )


if __name__ == "__main__":
    main()

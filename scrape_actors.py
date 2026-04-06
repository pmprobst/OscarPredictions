#!/usr/bin/env python3
"""Scrape cast lists for Best Picture nominees only (no award pages)."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from playwright.sync_api import sync_playwright

from oscar_scrape import (
    CAST_CSV_FILE,
    CAST_FIELDNAMES,
    _imdb_browser_context,
    extract_film_actor_rows,
    iter_best_picture_nominees,
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


def main():
    parser = argparse.ArgumentParser(
        description="Scrape IMDb full-credits cast for Best Picture nominees (skips precursor awards)."
    )
    parser.add_argument(
        "--year",
        type=int,
        metavar="Y",
        help="Single Oscar ceremony year. Default: 2026 through 1996.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Open a visible Chromium window (default: headless, no window).",
    )
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
        help="Process at most N Best Picture nominees per year (for testing).",
    )
    args = parser.parse_args()

    if args.year is not None:
        years = [args.year]
    else:
        years = list(range(2026, 1995, -1))

    cast_path = args.csv_cast
    existing_films = _load_existing_film_keys(cast_path)

    with open(cast_path, "a", newline="", encoding="utf-8") as cf:
        cast_writer = csv.DictWriter(cf, fieldnames=CAST_FIELDNAMES)
        if cf.tell() == 0:
            cast_writer.writeheader()

        with sync_playwright() as p:
            browser, context = _imdb_browser_context(p, headless=not args.headed)
            try:
                for year in years:
                    try:
                        for title, full_url, y in iter_best_picture_nominees(
                            context, year, max_movies=args.max_movies
                        ):
                            key = (str(int(y)), (title or "").strip())
                            if key in existing_films:
                                print(f"Skip (already in cast CSV): {title} ({y})")
                                continue
                            print(f"Cast: {title} ({y})")
                            rows_written = 0
                            for cast_row in extract_film_actor_rows(
                                context, full_url, y, title
                            ):
                                cast_writer.writerow(cast_row)
                                rows_written += 1
                            cf.flush()
                            if rows_written:
                                existing_films.add(key)
                    except Exception as e:
                        print(f"Error processing {year}: {e}")
            finally:
                context.close()
                browser.close()

    print(f"Film–actor pairs written incrementally to {cast_path}")


if __name__ == "__main__":
    main()

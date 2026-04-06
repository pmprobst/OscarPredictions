#!/usr/bin/env python3
"""Scrape cast lists for Best Picture nominees only (no award pages)."""

import argparse
import csv

from playwright.sync_api import sync_playwright

from oscar_scrape import (
    CAST_CSV_FILE,
    CAST_FIELDNAMES,
    _imdb_browser_context,
    extract_film_actor_rows,
    iter_best_picture_nominees,
)


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
        "--headless",
        action="store_true",
        help="Run Chromium without opening a window.",
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
    with open(cast_path, "a", newline="", encoding="utf-8") as cf:
        cast_writer = csv.DictWriter(cf, fieldnames=CAST_FIELDNAMES)
        if cf.tell() == 0:
            cast_writer.writeheader()

        with sync_playwright() as p:
            browser, context = _imdb_browser_context(p, args.headless)
            try:
                for year in years:
                    try:
                        for title, full_url, y in iter_best_picture_nominees(
                            context, year, max_movies=args.max_movies
                        ):
                            print(f"Cast: {title} ({y})")
                            for cast_row in extract_film_actor_rows(
                                context, full_url, y, title
                            ):
                                cast_writer.writerow(cast_row)
                            cf.flush()
                    except Exception as e:
                        print(f"Error processing {year}: {e}")
            finally:
                context.close()
                browser.close()

    print(f"Film–actor pairs written incrementally to {cast_path}")


if __name__ == "__main__":
    main()

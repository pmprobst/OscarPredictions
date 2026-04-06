#!/usr/bin/env python3
"""Scrape IMDb Best Picture nominees: precursor awards, director counts, optional cast CSV."""

import argparse
import csv

from playwright.sync_api import sync_playwright

from oscar_scrape import (
    CAST_CSV_FILE,
    CAST_FIELDNAMES,
    CSV_FILE,
    FIELDNAMES,
    _imdb_browser_context,
    get_movies_for_year,
)


def main():
    parser = argparse.ArgumentParser(
        description="Scrape IMDb Best Picture nominees and precursor / director award fields."
    )
    parser.add_argument(
        "--year",
        type=int,
        metavar="Y",
        help="Single Oscar ceremony year to scrape (for a quick test). Default: 2026 through 1996.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium without opening a window.",
    )
    parser.add_argument(
        "--csv",
        default=CSV_FILE,
        help=f"Output CSV path (default: {CSV_FILE}).",
    )
    parser.add_argument(
        "--csv-cast",
        default=CAST_CSV_FILE,
        help=f"Film–actor pairing CSV path (default: {CAST_CSV_FILE}). Omit writing cast by using scrape_actors.py instead.",
    )
    parser.add_argument(
        "--no-cast",
        action="store_true",
        help="Do not write the film–actor CSV (movies / awards only).",
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

    out_path = args.csv
    cast_path = args.csv_cast

    if args.no_cast:
        with open(out_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            if f.tell() == 0:
                writer.writeheader()
            with sync_playwright() as p:
                browser, context = _imdb_browser_context(p, args.headless)
                try:
                    for year in years:
                        try:
                            get_movies_for_year(
                                context, year, writer, cast_writer=None, max_movies=args.max_movies
                            )
                            f.flush()
                        except Exception as e:
                            print(f"Error processing {year}: {e}")
                finally:
                    context.close()
                    browser.close()
        print(f"Movies written incrementally to {out_path}")
        return

    with open(out_path, "a", newline="", encoding="utf-8") as f, open(
        cast_path, "a", newline="", encoding="utf-8"
    ) as cf:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        cast_writer = csv.DictWriter(cf, fieldnames=CAST_FIELDNAMES)

        if f.tell() == 0:
            writer.writeheader()
        if cf.tell() == 0:
            cast_writer.writeheader()

        with sync_playwright() as p:
            browser, context = _imdb_browser_context(p, args.headless)
            try:
                for year in years:
                    try:
                        get_movies_for_year(
                            context,
                            year,
                            writer,
                            cast_writer,
                            max_movies=args.max_movies,
                        )
                        f.flush()
                        cf.flush()
                    except Exception as e:
                        print(f"Error processing {year}: {e}")
            finally:
                context.close()
                browser.close()

    print(f"Movies written incrementally to {out_path}")
    print(f"Film–actor pairs written incrementally to {cast_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Scrape IMDb Best Picture nominees: precursor awards, director counts, optional cast CSV."""

from __future__ import annotations

import argparse
import csv
from typing import Sequence

from oscar_predictions.cliutil import (
    add_browser_args_movies_style,
    resolve_headless_movies_style,
)
from oscar_predictions.csvutil import count_csv_data_rows
from oscar_predictions.oscar_scrape import (
    CAST_CSV_FILE,
    CAST_FIELDNAMES,
    CSV_FILE,
    FIELDNAMES,
    _imdb_browser_context,
    get_movies_for_year,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape IMDb Best Picture nominees and precursor / director award fields."
    )
    parser.add_argument(
        "--year",
        type=int,
        metavar="Y",
        help="Single Oscar ceremony year to scrape (for a quick test). Default: 2026 through 1996.",
    )
    add_browser_args_movies_style(parser)
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
    return parser.parse_args(argv)


def run_scrape_movies(
    *,
    year: int | None = None,
    headless: bool = False,
    csv_path: str = CSV_FILE,
    csv_cast: str = CAST_CSV_FILE,
    no_cast: bool = False,
    max_movies: int | None = None,
) -> dict[str, int | str | bool]:
    if year is not None:
        years = [year]
    else:
        years = list(range(2026, 1995, -1))

    out_path = csv_path
    cast_path = csv_cast
    movies_before = count_csv_data_rows(out_path)
    cast_before = count_csv_data_rows(cast_path) if not no_cast else 0

    if no_cast:
        from playwright.sync_api import sync_playwright

        with open(out_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            if f.tell() == 0:
                writer.writeheader()
            with sync_playwright() as p:
                browser, context = _imdb_browser_context(p, headless)
                try:
                    for y in years:
                        try:
                            get_movies_for_year(
                                context, y, writer, cast_writer=None, max_movies=max_movies
                            )
                            f.flush()
                        except Exception as e:
                            print(f"Error processing {y}: {e}")
                finally:
                    context.close()
                    browser.close()
        movies_after = count_csv_data_rows(out_path)
        rows_added = max(0, movies_after - movies_before)
        print(f"Movies written incrementally to {out_path}")
        return {
            "rows_added": rows_added,
            "movies_rows_added": rows_added,
            "cast_rows_added": 0,
            "output_movies": out_path,
            "output_cast": cast_path,
            "no_cast": True,
        }

    with open(out_path, "a", newline="", encoding="utf-8") as f, open(
        cast_path, "a", newline="", encoding="utf-8"
    ) as cf:
        from playwright.sync_api import sync_playwright

        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        cast_writer = csv.DictWriter(cf, fieldnames=CAST_FIELDNAMES)

        if f.tell() == 0:
            writer.writeheader()
        if cf.tell() == 0:
            cast_writer.writeheader()

        with sync_playwright() as p:
            browser, context = _imdb_browser_context(p, headless)
            try:
                for y in years:
                    try:
                        get_movies_for_year(
                            context,
                            y,
                            writer,
                            cast_writer,
                            max_movies=max_movies,
                        )
                        f.flush()
                        cf.flush()
                    except Exception as e:
                        print(f"Error processing {y}: {e}")
            finally:
                context.close()
                browser.close()

    print(f"Movies written incrementally to {out_path}")
    print(f"Film–actor pairs written incrementally to {cast_path}")
    movies_after = count_csv_data_rows(out_path)
    cast_after = count_csv_data_rows(cast_path)
    movies_added = max(0, movies_after - movies_before)
    cast_added = max(0, cast_after - cast_before)
    return {
        "rows_added": movies_added + cast_added,
        "movies_rows_added": movies_added,
        "cast_rows_added": cast_added,
        "output_movies": out_path,
        "output_cast": cast_path,
        "no_cast": False,
    }


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    run_scrape_movies(
        year=args.year,
        headless=resolve_headless_movies_style(args),
        csv_path=args.csv,
        csv_cast=args.csv_cast,
        no_cast=args.no_cast,
        max_movies=args.max_movies,
    )


if __name__ == "__main__":
    main()

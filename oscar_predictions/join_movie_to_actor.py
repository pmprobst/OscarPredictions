#!/usr/bin/env python3
"""
Join movies.csv to aggregated cast award totals: for each nominated film (movies row),
sum every maj_* / grp_* column across all rows in film_actors_awards_sums_up_to_that_point.csv
that match on year and film title.

Default is a left join from movies.csv (zeros when no cast match). Use --inner to keep only
films with at least one cast row in the sums file.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from typing import Sequence

from oscar_predictions.csvutil import missing_required_columns
from oscar_predictions.oscar_scrape import CSV_FILE

DEFAULT_SUMS = "film_actors_awards_sums_up_to_that_point.csv"
DEFAULT_OUTPUT = "movies_with_cast_award_totals.csv"

SUMS_KEY_COLS = frozenset({"year", "film_title", "actor_name", "actor_imdb_url"})
MOVIES_REQUIRED = frozenset({"title", "year"})


def _parse_int_cell(s: str) -> int:
    s = (s or "").strip()
    if not s:
        return 0
    return int(s)


def load_sums_aggregates(
    sums_path: str,
) -> tuple[list[str], dict[tuple[int, str], tuple[list[int], int]]]:
    """
    Return (feature_column_names in header order, agg: (year, film_title) -> (totals, cast_row_count)).
    """
    with open(sums_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit(f"Empty or invalid sums CSV: {sums_path}")
        fn = reader.fieldnames
        need = {"year", "film_title"}
        miss = missing_required_columns(fn, need)
        if miss:
            raise SystemExit(f"{sums_path} missing columns: {miss}")
        feature_cols = [c for c in fn if c not in SUMS_KEY_COLS]
        if not feature_cols:
            raise SystemExit(f"No feature columns after keys in {sums_path}")

        n = len(feature_cols)
        # key -> [totals list, cast count]
        buckets: dict[tuple[int, str], list] = defaultdict(
            lambda: [[0] * n, 0]
        )

        for row in reader:
            raw_y = (row.get("year") or "").strip()
            try:
                y = int(raw_y)
            except ValueError:
                continue
            title = (row.get("film_title") or "").strip()
            key = (y, title)
            b = buckets[key]
            for i, col in enumerate(feature_cols):
                b[0][i] += _parse_int_cell(row.get(col, ""))
            b[1] += 1

        out: dict[tuple[int, str], tuple[list[int], int]] = {
            k: (v[0], v[1]) for k, v in buckets.items()
        }
        return feature_cols, out


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="One row per movie from movies.csv with summed maj_/grp_ columns over credited cast."
    )
    parser.add_argument("--movies", default=CSV_FILE, help=f"Movies CSV (default: {CSV_FILE}).")
    parser.add_argument(
        "--film-actors-sums",
        default=DEFAULT_SUMS,
        dest="film_actors_sums",
        help=f"Film–cast cumulative sums CSV (default: {DEFAULT_SUMS}).",
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help=f"Output CSV (default: {DEFAULT_OUTPUT}).")
    parser.add_argument(
        "--inner",
        action="store_true",
        help="Only output movies that have at least one matching row in the sums file.",
    )
    parser.add_argument(
        "--no-cast-count",
        action="store_true",
        help="Omit cast_row_count column from output.",
    )
    return parser.parse_args(argv)


def run_join_movie_to_actor(
    *,
    movies: str = CSV_FILE,
    film_actors_sums: str = DEFAULT_SUMS,
    output: str = DEFAULT_OUTPUT,
    inner: bool = False,
    no_cast_count: bool = False,
) -> dict[str, int | str | bool]:
    feature_cols, aggregates = load_sums_aggregates(film_actors_sums)
    nfeat = len(feature_cols)
    zeros = [0] * nfeat

    with open(movies, newline="", encoding="utf-8") as mf:
        m_reader = csv.DictReader(mf)
        if not m_reader.fieldnames:
            raise SystemExit(f"Empty or invalid movies CSV: {movies}")
        movie_cols = list(m_reader.fieldnames)
        miss_m = missing_required_columns(movie_cols, MOVIES_REQUIRED)
        if miss_m:
            raise SystemExit(f"{movies} missing columns: {miss_m}")

        include_count = not no_cast_count
        extra = [] if not include_count else ["cast_row_count"]
        out_fieldnames = movie_cols + extra + feature_cols

        written = 0
        with open(output, "w", newline="", encoding="utf-8") as outf:
            writer = csv.DictWriter(outf, fieldnames=out_fieldnames)
            writer.writeheader()

            for row in m_reader:
                raw_y = (row.get("year") or "").strip()
                try:
                    y = int(raw_y)
                except ValueError:
                    if inner:
                        continue
                    out_row = {c: row.get(c, "") for c in movie_cols}
                    if include_count:
                        out_row["cast_row_count"] = "0"
                    for i, c in enumerate(feature_cols):
                        out_row[c] = "0"
                    writer.writerow(out_row)
                    written += 1
                    continue

                title = (row.get("title") or "").strip()
                key = (y, title)
                if key not in aggregates:
                    if inner:
                        continue
                    totals, count = zeros, 0
                else:
                    totals, count = aggregates[key]

                out_row = {c: row.get(c, "") for c in movie_cols}
                if include_count:
                    out_row["cast_row_count"] = str(count)
                for i, c in enumerate(feature_cols):
                    out_row[c] = str(totals[i])
                writer.writerow(out_row)
                written += 1

    print(f"Wrote {written} rows to {output}")
    return {
        "rows_added": written,
        "written_rows": written,
        "inner_join": inner,
        "include_cast_count": not no_cast_count,
        "output_movies_with_totals": output,
    }


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    run_join_movie_to_actor(
        movies=args.movies,
        film_actors_sums=args.film_actors_sums,
        output=args.output,
        inner=args.inner,
        no_cast_count=args.no_cast_count,
    )


if __name__ == "__main__":
    main()

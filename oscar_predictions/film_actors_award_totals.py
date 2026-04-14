#!/usr/bin/env python3
"""
Join film_actors.csv to actor_year_award_matrix.csv: for each film–cast row with film
year F, append cumulative maj_* / grp_* counts for that actor summed over all award
years y where y <= F (career totals through award-year F, excluding later years).

Inputs are read-only. Regenerate actor_year_award_matrix.csv before this if awards changed.
"""

from __future__ import annotations

import argparse
import bisect
import csv
from collections import defaultdict
from typing import Sequence

from oscar_predictions.csvutil import missing_required_columns
from oscar_predictions.oscar_scrape import CAST_CSV_FILE, CAST_FIELDNAMES

DEFAULT_MATRIX = "actor_year_award_matrix.csv"
DEFAULT_OUTPUT = "film_actors_awards_sums_up_to_that_point.csv"

MATRIX_KEY_COLS = ("actor_name", "actor_imdb_url", "year")


def _parse_int(s: str, ctx: str) -> int:
    s = (s or "").strip()
    if not s:
        raise ValueError(f"empty year in {ctx}")
    return int(s)


def load_matrix_prefixes(
    matrix_path: str,
) -> tuple[list[str], dict[str, tuple[list[int], list[list[int]]]]]:
    """
    Return (feature_column_names, per_url: (sorted_years, prefix_sum_vectors)).
    prefix[i] is cumulative sum for award years through sorted_years[i] inclusive.
    """
    with open(matrix_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit(f"Empty or invalid matrix: {matrix_path}")
        feature_cols = [c for c in reader.fieldnames if c not in MATRIX_KEY_COLS]
        if not feature_cols:
            raise SystemExit(f"No feature columns in matrix after keys: {matrix_path}")

        # url -> year -> vector (merge duplicate years)
        by_url_year: dict[str, dict[int, list[int]]] = defaultdict(
            lambda: defaultdict(lambda: [0] * len(feature_cols))
        )

        for row in reader:
            url = (row.get("actor_imdb_url") or "").strip()
            if not url:
                continue
            y = _parse_int(row.get("year", ""), "matrix row")
            vec = [_parse_int(row.get(c, "0"), c) for c in feature_cols]
            bucket = by_url_year[url][y]
            for i, v in enumerate(vec):
                bucket[i] += v

    prefixes: dict[str, tuple[list[int], list[list[int]]]] = {}
    n = len(feature_cols)

    for url, year_map in by_url_year.items():
        years_sorted = sorted(year_map.keys())
        prefix_vecs: list[list[int]] = []
        running = [0] * n
        for y in years_sorted:
            rowv = year_map[y]
            for i in range(n):
                running[i] += rowv[i]
            prefix_vecs.append(list(running))
        prefixes[url] = (years_sorted, prefix_vecs)

    return feature_cols, prefixes


def cumulative_for_film_year(
    prefixes: dict[str, tuple[list[int], list[list[int]]]],
    url: str,
    film_year: int,
    n_features: int,
) -> list[int]:
    """Return cumulative feature vector for actor at url through award years <= film_year."""
    zero = [0] * n_features
    if url not in prefixes:
        return zero
    years, pref = prefixes[url]
    if not years:
        return zero
    idx = bisect.bisect_right(years, film_year) - 1
    if idx < 0:
        return zero
    return pref[idx]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append cumulative actor-year matrix columns to each film_actors row (award years <= film year)."
    )
    parser.add_argument("--film-actors", default=CAST_CSV_FILE, help="Cast CSV (default: film_actors.csv).")
    parser.add_argument("--matrix", default=DEFAULT_MATRIX, help="Actor-year matrix CSV.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output CSV path.")
    parser.add_argument("--max-rows", type=int, default=None, metavar="N", help="Process at most N film_actors rows.")
    return parser.parse_args(argv)


def run_film_actors_award_totals(
    *,
    film_actors: str = CAST_CSV_FILE,
    matrix: str = DEFAULT_MATRIX,
    output: str = DEFAULT_OUTPUT,
    max_rows: int | None = None,
) -> None:
    feature_cols, prefixes = load_matrix_prefixes(matrix)
    nfeat = len(feature_cols)
    out_fieldnames = list(CAST_FIELDNAMES) + feature_cols

    written = 0

    with open(film_actors, newline="", encoding="utf-8") as inf, open(
        output, "w", newline="", encoding="utf-8"
    ) as outf:
        reader = csv.DictReader(inf)
        miss = missing_required_columns(reader.fieldnames, set(CAST_FIELDNAMES))
        if miss:
            raise SystemExit(f"--film-actors missing columns: {miss}")

        writer = csv.DictWriter(outf, fieldnames=out_fieldnames)
        writer.writeheader()

        for row in reader:
            if max_rows is not None and written >= max_rows:
                break
            url = (row.get("actor_imdb_url") or "").strip()
            name_cast = (row.get("actor_name") or "").strip()
            try:
                fy = _parse_int(row.get("year", ""), f"film_actors row {written + 2}")
            except ValueError as e:
                raise SystemExit(str(e)) from e

            vec = cumulative_for_film_year(prefixes, url, fy, nfeat)

            out_row: dict[str, object] = {
                "year": row.get("year", ""),
                "film_title": row.get("film_title", ""),
                "actor_name": name_cast,
                "actor_imdb_url": url,
            }
            for c, v in zip(feature_cols, vec):
                out_row[c] = v
            writer.writerow(out_row)
            written += 1

    print(f"Wrote {written} rows to {output} ({nfeat} feature columns).")


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    run_film_actors_award_totals(
        film_actors=args.film_actors,
        matrix=args.matrix,
        output=args.output,
        max_rows=args.max_rows,
    )


if __name__ == "__main__":
    main()

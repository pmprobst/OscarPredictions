#!/usr/bin/env python3
"""
Read actor_awards.csv (read-only), extract the award ceremony name from each award
string with a regex, aggregate counts per distinct ceremony, and write award_show_counts.csv.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from typing import Sequence

from oscar_predictions.award_regex import CEREMONY_PATTERN, CEREMONY_RE
from oscar_predictions.oscar_scrape import ACTOR_AWARDS_CSV_FILE, ACTOR_AWARD_FIELDNAMES

DEFAULT_CEREMONY_PATTERN = CEREMONY_PATTERN

COUNTS_FIELDNAMES = ["award_show", "count"]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build award_show -> count catalog from actor_awards.csv."
    )
    parser.add_argument(
        "--input",
        default=ACTOR_AWARDS_CSV_FILE,
        help=f"Input CSV path (default: {ACTOR_AWARDS_CSV_FILE}).",
    )
    parser.add_argument(
        "--counts-out",
        default="award_show_counts.csv",
        help="Output CSV: award_show, count (default: award_show_counts.csv).",
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_CEREMONY_PATTERN,
        help="Regex with one capture group for the ceremony name (default: IMDb-style prefix).",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        metavar="N",
        help="Process at most N data rows (after header).",
    )
    return parser.parse_args(argv)


def run_award_show_counts(
    *,
    input_path: str = ACTOR_AWARDS_CSV_FILE,
    counts_out: str = "award_show_counts.csv",
    pattern: str = DEFAULT_CEREMONY_PATTERN,
    max_rows: int | None = None,
) -> dict[str, int | str]:
    try:
        ceremony_re = CEREMONY_RE if pattern == DEFAULT_CEREMONY_PATTERN else re.compile(pattern)
    except re.error as e:
        raise SystemExit(f"Invalid --pattern: {e}") from e

    counts: Counter[str] = Counter()
    processed = 0
    unmatched = 0

    with open(input_path, newline="", encoding="utf-8") as inf:
        reader = csv.DictReader(inf)
        missing = [c for c in ACTOR_AWARD_FIELDNAMES if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"Input CSV missing columns: {missing}")

        for row in reader:
            if max_rows is not None and processed >= max_rows:
                break
            processed += 1
            award = (row.get("award") or "").strip()
            m = ceremony_re.match(award)
            if m:
                counts[m.group(1)] += 1
            else:
                unmatched += 1

    sorted_rows = sorted(
        counts.items(),
        key=lambda kv: (-kv[1], kv[0]),
    )
    with open(counts_out, "w", newline="", encoding="utf-8") as outf:
        w = csv.DictWriter(outf, fieldnames=COUNTS_FIELDNAMES)
        w.writeheader()
        for show, n in sorted_rows:
            w.writerow({"award_show": show, "count": n})

    print(
        f"Processed {processed} rows; {len(counts)} distinct award_show; "
        f"{unmatched} regex non-matches; wrote {counts_out}"
    )
    return {
        "rows_added": len(sorted_rows),
        "processed_rows": processed,
        "distinct_shows": len(counts),
        "unmatched_rows": unmatched,
        "output_counts": counts_out,
    }


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    run_award_show_counts(
        input_path=args.input,
        counts_out=args.counts_out,
        pattern=args.pattern,
        max_rows=args.max_rows,
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Build actor-year rows with maj_* and grp_* nomination/win counts from actor_awards.csv.
Major ceremonies get dedicated column pairs; all other ceremonies roll into group buckets.
actor_awards.csv is read-only.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

from award_groups import GROUP_KEYS, classify_group, slugify_award_show
from award_regex import parse_ceremony
from oscar_scrape import ACTOR_AWARDS_CSV_FILE, ACTOR_AWARD_FIELDNAMES

DEFAULT_MAJOR_LIST = "major_award_shows.txt"
DEFAULT_UNPARSED = "actor_award_unparsed.csv"


def load_major_award_shows(path: str | Path) -> list[str]:
    out: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def build_major_slugs(majors: list[str]) -> tuple[list[str], dict[str, str]]:
    """Return ordered slug list and award_show -> slug."""
    used: set[str] = set()
    slugs: list[str] = []
    show_to_slug: dict[str, str] = {}
    for show in majors:
        slug = slugify_award_show(show, "maj_", used)
        slugs.append(slug)
        show_to_slug[show] = slug
    return slugs, show_to_slug


def make_empty_row(major_slugs: list[str]) -> dict[str, int]:
    d: dict[str, int] = {}
    for s in major_slugs:
        d[f"{s}_noms"] = 0
        d[f"{s}_wins"] = 0
    for g in GROUP_KEYS:
        d[f"grp_{g}_noms"] = 0
        d[f"grp_{g}_wins"] = 0
    return d


def row_increment(row: dict[str, int], key: str, is_win: bool) -> None:
    suffix = "wins" if is_win else "noms"
    row[f"{key}_{suffix}"] += 1


def sum_feature_counts(row: dict[str, int]) -> int:
    return sum(row.values())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Actor-year CSV: major ceremony columns + grouped award columns (noms/wins counts)."
    )
    parser.add_argument("--input", default=ACTOR_AWARDS_CSV_FILE, help="actor_awards CSV (read-only).")
    parser.add_argument("--output", default="actor_year_award_matrix.csv", help="Output wide CSV.")
    parser.add_argument("--major-list", default=DEFAULT_MAJOR_LIST, help="Text file: one major award_show per line.")
    parser.add_argument("--unparsed-out", default=DEFAULT_UNPARSED, help="Rows where ceremony regex did not match.")
    parser.add_argument("--max-rows", type=int, default=None, metavar="N", help="Process at most N award rows.")
    args = parser.parse_args()

    majors = load_major_award_shows(args.major_list)
    if not majors:
        raise SystemExit(f"No major award shows loaded from {args.major_list}")
    major_slugs, major_show_to_slug = build_major_slugs(majors)
    major_set = set(majors)

    # (actor_imdb_url, actor_name, year) -> counts
    agg: dict[tuple[str, str, str], dict[str, int]] = defaultdict(
        lambda: make_empty_row(major_slugs)
    )

    matched_rows = 0
    processed = 0
    unparsed_count = 0

    with open(args.input, newline="", encoding="utf-8") as inf, open(
        args.unparsed_out, "w", newline="", encoding="utf-8"
    ) as unf:
        reader = csv.DictReader(inf)
        missing = [c for c in ACTOR_AWARD_FIELDNAMES if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"Input missing columns: {missing}")

        uwriter = csv.DictWriter(unf, fieldnames=ACTOR_AWARD_FIELDNAMES)
        uwriter.writeheader()

        for row in reader:
            if args.max_rows is not None and processed >= args.max_rows:
                break
            processed += 1

            award = (row.get("award") or "").strip()
            ceremony = parse_ceremony(award)
            if not ceremony:
                unparsed_count += 1
                uwriter.writerow({k: row.get(k, "") for k in ACTOR_AWARD_FIELDNAMES})
                continue

            matched_rows += 1
            outcome = (row.get("outcome") or "").strip().lower()
            is_win = outcome == "won"
            is_nom = outcome == "nominated"
            if not is_win and not is_nom:
                unparsed_count += 1
                uwriter.writerow({k: row.get(k, "") for k in ACTOR_AWARD_FIELDNAMES})
                continue

            url = (row.get("actor_imdb_url") or "").strip()
            name = (row.get("actor_name") or "").strip()
            year = (row.get("year") or "").strip()
            key = (url, name, year)
            bucket = agg[key]

            if ceremony in major_set:
                slug = major_show_to_slug[ceremony]
                row_increment(bucket, slug, is_win)
            else:
                g = classify_group(ceremony)
                row_increment(bucket, f"grp_{g}", is_win)

    # column order
    key_fieldnames = ["actor_name", "actor_imdb_url", "year"]
    major_fieldnames: list[str] = []
    for s in major_slugs:
        major_fieldnames.extend([f"{s}_noms", f"{s}_wins"])
    group_fieldnames: list[str] = []
    for g in GROUP_KEYS:
        group_fieldnames.extend([f"grp_{g}_noms", f"grp_{g}_wins"])
    fieldnames = key_fieldnames + major_fieldnames + group_fieldnames

    matrix_sum = 0
    with open(args.output, "w", newline="", encoding="utf-8") as outf:
        writer = csv.DictWriter(outf, fieldnames=fieldnames)
        writer.writeheader()
        for (url, name, year) in sorted(agg.keys(), key=lambda k: (k[2], k[1], k[0])):
            counts = agg[(url, name, year)]
            out_row = {
                "actor_name": name,
                "actor_imdb_url": url,
                "year": year,
                **{fn: counts.get(fn, 0) for fn in major_fieldnames + group_fieldnames},
            }
            matrix_sum += sum_feature_counts(counts)
            writer.writerow(out_row)

    # Verification: each matched input row adds exactly 1 to some noms or wins cell.
    if matrix_sum != matched_rows:
        print(
            f"WARNING: sum of matrix counts ({matrix_sum}) != matched award rows ({matched_rows}).",
            file=sys.stderr,
        )
    else:
        print(f"OK: matrix total noms+wins ({matrix_sum}) equals matched rows ({matched_rows}).")

    print(
        f"Processed {processed} award rows; {matched_rows} regex-matched; "
        f"{unparsed_count} unparsed or bad outcome; {len(agg)} actor-year rows -> {args.output}"
    )


if __name__ == "__main__":
    main()

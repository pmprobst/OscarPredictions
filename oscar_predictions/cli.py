"""Command-line interface for streamlined Oscar pipeline usage."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from oscar_predictions.cliutil import add_browser_args, resolve_headless
from oscar_predictions.config import SyncConfig, SyncPaths
from oscar_predictions.sync import run_sync


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oscar", description="OscarPredictions unified CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    sync = sub.add_parser("sync", help="Run end-to-end incremental pipeline sync.")
    sync.add_argument("--year", type=int, default=None, help="Target a single ceremony year.")
    add_browser_args(sync)
    sync.add_argument("--dry-run", action="store_true", help="Show stage plan without executing.")
    sync.add_argument(
        "--rebuild-derived",
        action="store_true",
        help="Force derived-table rebuild stages even if no new upstream rows.",
    )
    sync.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue running later stages after a stage failure.",
    )
    sync.add_argument(
        "--include-counts",
        action="store_true",
        help="Also rebuild award_show_counts.csv in sync runs.",
    )
    sync.add_argument("--max-movies", type=int, default=None, help="Cap per-run movie scraping attempts.")
    sync.add_argument("--max-actors", type=int, default=None, help="Cap per-run actor scraping attempts.")
    sync.add_argument("--movies", default="movies.csv", help="Movies CSV path.")
    sync.add_argument("--cast", default="film_actors.csv", help="Film-actor cast CSV path.")
    sync.add_argument("--actor-awards", default="actor_awards.csv", help="Actor awards CSV path.")
    sync.add_argument("--no-award-actors", default="no_award_actors.csv", help="No-award registry CSV path.")
    sync.add_argument("--matrix", default="actor_year_award_matrix.csv", help="Actor-year matrix output path.")
    sync.add_argument(
        "--film-actor-totals",
        default="film_actors_awards_sums_up_to_that_point.csv",
        help="Film-actor cumulative output path.",
    )
    sync.add_argument(
        "--movie-totals",
        default="movies_with_cast_award_totals.csv",
        help="Movie-level joined totals output path.",
    )
    sync.add_argument("--counts", default="award_show_counts.csv", help="Award show counts output path.")
    sync.add_argument("--major-list", default="major_award_shows.txt", help="Major award list path.")
    sync.add_argument(
        "--state-file",
        default=".oscar_sync_state.json",
        help="Checkpoint state file for resumable sync.",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def _build_config(args: argparse.Namespace) -> SyncConfig:
    paths = SyncPaths(
        movies=args.movies,
        cast=args.cast,
        actor_awards=args.actor_awards,
        no_award_actors=args.no_award_actors,
        actor_year_matrix=args.matrix,
        film_actor_totals=args.film_actor_totals,
        movie_totals=args.movie_totals,
        award_show_counts=args.counts,
        major_list=args.major_list,
        state_file=args.state_file,
    )
    return SyncConfig(
        paths=paths,
        year=args.year,
        headless=resolve_headless(args, default_headless=True),
        dry_run=args.dry_run,
        rebuild_derived=args.rebuild_derived,
        continue_on_error=args.continue_on_error,
        include_counts=args.include_counts,
        max_movies=args.max_movies,
        max_actors=args.max_actors,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "sync":
        report = run_sync(_build_config(args))
        for stage in report.stage_summaries:
            status = "SKIP" if stage.skipped else "RUN"
            print(f"[{status}] {stage.name} {stage.details if stage.details else ''}".rstrip())
            if stage.errors:
                for err in stage.errors:
                    print(f"  error: {err}")
        return 0
    raise SystemExit(f"Unknown command: {args.command}")

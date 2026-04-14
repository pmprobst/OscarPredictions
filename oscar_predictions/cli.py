"""Command-line interface for streamlined Oscar pipeline usage."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from oscar_predictions.cliutil import add_browser_args, resolve_headless
from oscar_predictions.config import SyncConfig, SyncPaths, sync_paths_from_workspace
from oscar_predictions.features import run_build_features
from oscar_predictions.reset_workspace import run_reset_workspace
from oscar_predictions.sync import run_sync
from oscar_predictions.updates import run_check_updates
from oscar_predictions.workspace import DataWorkspace


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
    sync.add_argument(
        "--workspace-dir",
        default=".",
        help="Workspace directory containing input/output CSV files (default: current dir).",
    )

    init_data = sub.add_parser("init-data", help="Copy bundled base data (<=2023) into workspace.")
    init_data.add_argument(
        "--workspace-dir",
        default=".",
        help="Workspace directory to initialize (default: current dir).",
    )
    init_data.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing base files in workspace.",
    )

    build_features = sub.add_parser("build-features", help="Generate post-cleaning feature outputs.")
    build_features.add_argument(
        "--workspace-dir",
        default=".",
        help="Workspace directory containing base CSV files (default: current dir).",
    )

    reset_ws = sub.add_parser(
        "reset",
        help="Trim base CSVs to cutoff year, prune no_award actors, delete derived outputs and sync state.",
    )
    reset_ws.add_argument("--workspace-dir", default=".", help="Workspace directory (default: current dir).")
    reset_ws.add_argument(
        "--cutoff-year",
        type=int,
        default=2023,
        help="Keep rows with year <= this value in movies, film_actors, and actor_awards (default: 2023).",
    )
    reset_ws.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without modifying files.",
    )

    check_updates = sub.add_parser("check-updates", help="Detect and ingest new nominee years, then rebuild.")
    check_updates.add_argument(
        "--workspace-dir",
        default=".",
        help="Workspace directory containing CSV files (default: current dir).",
    )
    add_browser_args(check_updates)
    check_updates.add_argument("--max-movies", type=int, default=None, help="Cap per-year movie scrape attempts.")
    check_updates.add_argument("--max-actors", type=int, default=None, help="Cap actor scrape attempts.")

    model = sub.add_parser("model", help="Run production modeling on movies_with_cast_award_totals.csv.")
    model.add_argument("--workspace-dir", default=".", help="Workspace directory (default: current dir).")
    model.add_argument("--seed", type=int, default=42, help="Random seed for train/test split.")
    model.add_argument("--test-size", type=float, default=0.25, help="Test split fraction.")
    model.add_argument(
        "--report-json",
        default=None,
        help="Optional path to write modeling metrics JSON.",
    )
    model.add_argument(
        "--predictions-csv",
        default=None,
        help="Optional path to write per-row predictions CSV.",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def _build_config(args: argparse.Namespace) -> SyncConfig:
    if args.workspace_dir and args.workspace_dir != ".":
        paths = sync_paths_from_workspace(args.workspace_dir)
    else:
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
    if args.command == "init-data":
        ws = DataWorkspace.from_path(args.workspace_dir)
        result = ws.init_base_data(overwrite=args.overwrite)
        print(f"Initialized workspace {ws.root}")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "build-features":
        ws = DataWorkspace.from_path(args.workspace_dir)
        result = run_build_features(ws)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "reset":
        ws = DataWorkspace.from_path(args.workspace_dir)
        result = run_reset_workspace(ws, cutoff_year=args.cutoff_year, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "check-updates":
        ws = DataWorkspace.from_path(args.workspace_dir)
        result = run_check_updates(
            ws,
            headless=resolve_headless(args, default_headless=True),
            max_movies=args.max_movies,
            max_actors=args.max_actors,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "model":
        from oscar_predictions.modeling import run_model

        ws = DataWorkspace.from_path(args.workspace_dir)
        report = run_model(
            ws,
            seed=args.seed,
            test_size=args.test_size,
            report_path=args.report_json,
            predictions_path=args.predictions_csv,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    raise SystemExit(f"Unknown command: {args.command}")

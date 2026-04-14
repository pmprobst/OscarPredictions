"""Single-command sync orchestration and planner logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from oscar_predictions.actor_year_award_matrix import run_actor_year_award_matrix
from oscar_predictions.award_show_counts import run_award_show_counts
from oscar_predictions.config import SyncConfig
from oscar_predictions.csvutil import has_year_value
from oscar_predictions.film_actors_award_totals import run_film_actors_award_totals
from oscar_predictions.join_movie_to_actor import run_join_movie_to_actor
from oscar_predictions.models import StageSummary, SyncReport
from oscar_predictions.scrape_actor_awards import run_scrape_actor_awards
from oscar_predictions.scrape_actors import run_scrape_actors
from oscar_predictions.scrape_movies import run_scrape_movies


def _load_state(path: Path) -> dict:
    if not path.is_file():
        return {"completed_stages": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"completed_stages": []}


def _save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def _stage_completed(state: dict, stage_name: str) -> bool:
    return stage_name in state.get("completed_stages", [])


def _mark_completed(state: dict, stage_name: str) -> None:
    completed = set(state.get("completed_stages", []))
    completed.add(stage_name)
    state["completed_stages"] = sorted(completed)


def run_sync(config: SyncConfig) -> SyncReport:
    report = SyncReport(dry_run=config.dry_run)
    state_path = config.state_file_path()
    state = _load_state(state_path)
    state_key = {
        "year": config.year,
        "movies": config.paths.movies,
        "cast": config.paths.cast,
        "actor_awards": config.paths.actor_awards,
    }
    if state.get("state_key") != state_key:
        state = {"completed_stages": [], "state_key": state_key}

    target_year = config.year
    have_movies_for_year = (
        True if target_year is None else has_year_value(config.paths.movies, target_year)
    )

    def run_stage(
        name: str,
        should_run: bool,
        fn: Callable[[], dict],
    ) -> dict:
        if not should_run:
            summary = StageSummary(name=name, ran=False, skipped=True, details={"reason": "planner_skip"})
            report.stage_summaries.append(summary)
            return {}
        if _stage_completed(state, name):
            summary = StageSummary(
                name=name,
                ran=False,
                skipped=True,
                details={"reason": "checkpoint_skip"},
            )
            report.stage_summaries.append(summary)
            return {}
        if config.dry_run:
            summary = StageSummary(name=name, ran=False, skipped=True, details={"reason": "dry_run"})
            report.stage_summaries.append(summary)
            return {}
        try:
            details = fn()
            summary = StageSummary(name=name, ran=True, skipped=False, details=details)
            report.stage_summaries.append(summary)
            _mark_completed(state, name)
            _save_state(state_path, state)
            return details
        except Exception as exc:  # pragma: no cover - safety net
            summary = StageSummary(name=name, ran=True, skipped=False, errors=[str(exc)])
            report.stage_summaries.append(summary)
            if not config.continue_on_error:
                raise
            return {}

    movies_details = run_stage(
        "scrape_movies",
        should_run=(target_year is None) or (not have_movies_for_year),
        fn=lambda: run_scrape_movies(
            year=target_year,
            headless=config.headless,
            csv_path=config.paths.movies,
            csv_cast=config.paths.cast,
            no_cast=False,
            max_movies=config.max_movies,
        ),
    )
    actors_details = run_stage(
        "scrape_actors",
        should_run=True,
        fn=lambda: run_scrape_actors(
            movies=config.paths.movies,
            year=target_year,
            headless=config.headless,
            csv_cast=config.paths.cast,
            max_movies=config.max_movies,
            no_award_csv=config.paths.no_award_actors,
            skip_no_award_prune=False,
        ),
    )
    awards_details = run_stage(
        "scrape_actor_awards",
        should_run=True,
        fn=lambda: run_scrape_actor_awards(
            input_path=config.paths.cast,
            output_path=config.paths.actor_awards,
            no_award_output=config.paths.no_award_actors,
            force_rescrape=False,
            headless=config.headless,
            max_actors=config.max_actors,
        ),
    )

    report.upstream_changed = any(
        int(d.get("rows_added", 0)) > 0
        for d in (movies_details, actors_details, awards_details)
    )
    should_rebuild = config.rebuild_derived or report.upstream_changed

    run_stage(
        "actor_year_award_matrix",
        should_run=should_rebuild,
        fn=lambda: run_actor_year_award_matrix(
            input_path=config.paths.actor_awards,
            output_path=config.paths.actor_year_matrix,
            major_list=config.paths.major_list,
            max_rows=None,
        ),
    )
    run_stage(
        "film_actors_award_totals",
        should_run=should_rebuild,
        fn=lambda: run_film_actors_award_totals(
            film_actors=config.paths.cast,
            matrix=config.paths.actor_year_matrix,
            output=config.paths.film_actor_totals,
            max_rows=None,
        ),
    )
    run_stage(
        "join_movie_to_actor",
        should_run=should_rebuild,
        fn=lambda: run_join_movie_to_actor(
            movies=config.paths.movies,
            film_actors_sums=config.paths.film_actor_totals,
            output=config.paths.movie_totals,
            inner=False,
            no_cast_count=False,
        ),
    )
    run_stage(
        "award_show_counts",
        should_run=config.include_counts and should_rebuild,
        fn=lambda: run_award_show_counts(
            input_path=config.paths.actor_awards,
            counts_out=config.paths.award_show_counts,
            max_rows=None,
        ),
    )
    return report

"""Unified configuration model for CLI and sync orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from oscar_predictions.oscar_scrape import (
    ACTOR_AWARDS_CSV_FILE,
    CAST_CSV_FILE,
    CSV_FILE,
    NO_AWARD_ACTORS_CSV_FILE,
)


@dataclass(frozen=True)
class SyncPaths:
    movies: str = CSV_FILE
    cast: str = CAST_CSV_FILE
    actor_awards: str = ACTOR_AWARDS_CSV_FILE
    no_award_actors: str = NO_AWARD_ACTORS_CSV_FILE
    actor_year_matrix: str = "actor_year_award_matrix.csv"
    film_actor_totals: str = "film_actors_awards_sums_up_to_that_point.csv"
    movie_totals: str = "movies_with_cast_award_totals.csv"
    award_show_counts: str = "award_show_counts.csv"
    major_list: str = "major_award_shows.txt"
    state_file: str = ".oscar_sync_state.json"


@dataclass(frozen=True)
class SyncConfig:
    paths: SyncPaths
    year: int | None = None
    headless: bool = True
    dry_run: bool = False
    rebuild_derived: bool = False
    continue_on_error: bool = False
    include_counts: bool = False
    max_movies: int | None = None
    max_actors: int | None = None

    def state_file_path(self) -> Path:
        return Path(self.paths.state_file)


def sync_paths_from_workspace(workspace_root: str | Path) -> SyncPaths:
    from oscar_predictions.workspace import DataWorkspace

    ws = DataWorkspace.from_path(workspace_root)
    return SyncPaths(
        movies=str(ws.movies),
        cast=str(ws.cast),
        actor_awards=str(ws.actor_awards),
        no_award_actors=str(ws.no_award_actors),
        actor_year_matrix=str(ws.actor_year_matrix),
        film_actor_totals=str(ws.film_actor_totals),
        movie_totals=str(ws.movie_totals),
        award_show_counts=str(ws.award_show_counts),
        major_list=str(ws.major_list),
        state_file=str(ws.state_file),
    )

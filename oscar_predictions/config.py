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

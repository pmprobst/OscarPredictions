"""Workspace paths and file lifecycle for base/derived Oscar data."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from oscar_predictions.bundled_data import BASE_FILENAMES, bundled_base_resource, bundled_config_resource


@dataclass(frozen=True)
class DataWorkspace:
    root: Path

    @classmethod
    def from_path(cls, path: str | Path) -> "DataWorkspace":
        return cls(Path(path).expanduser().resolve())

    def ensure_exists(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def movies(self) -> Path:
        return self.root / "movies.csv"

    @property
    def cast(self) -> Path:
        return self.root / "film_actors.csv"

    @property
    def actor_awards(self) -> Path:
        return self.root / "actor_awards.csv"

    @property
    def no_award_actors(self) -> Path:
        return self.root / "no_award_actors.csv"

    @property
    def actor_year_matrix(self) -> Path:
        return self.root / "actor_year_award_matrix.csv"

    @property
    def film_actor_totals(self) -> Path:
        return self.root / "film_actors_awards_sums_up_to_that_point.csv"

    @property
    def movie_totals(self) -> Path:
        return self.root / "movies_with_cast_award_totals.csv"

    @property
    def award_show_counts(self) -> Path:
        return self.root / "award_show_counts.csv"

    @property
    def major_list(self) -> Path:
        return self.root / "major_award_shows.txt"

    @property
    def state_file(self) -> Path:
        return self.root / ".oscar_sync_state.json"

    def delete_derived_outputs(self) -> list[str]:
        removed: list[str] = []
        for p in (self.actor_year_matrix, self.film_actor_totals, self.movie_totals, self.award_show_counts):
            if p.exists():
                p.unlink()
                removed.append(str(p))
        return removed

    def init_base_data(self, *, overwrite: bool = False) -> dict[str, int | list[str]]:
        self.ensure_exists()
        copied = 0
        skipped = 0
        copied_files: list[str] = []
        skipped_files: list[str] = []
        for name in BASE_FILENAMES:
            dest = self.root / name
            if dest.exists() and not overwrite:
                skipped += 1
                skipped_files.append(name)
                continue
            src = bundled_base_resource(name)
            with src.open("rb") as fsrc, dest.open("wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)
            copied += 1
            copied_files.append(name)

        if not self.major_list.exists() or overwrite:
            src_cfg = bundled_config_resource("major_award_shows.txt")
            with src_cfg.open("rb") as fsrc, self.major_list.open("wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)
            copied += 1
            copied_files.append("major_award_shows.txt")
        else:
            skipped += 1
            skipped_files.append("major_award_shows.txt")

        return {
            "copied": copied,
            "skipped": skipped,
            "copied_files": copied_files,
            "skipped_files": skipped_files,
        }

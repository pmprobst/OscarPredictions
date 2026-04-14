"""Bundled package-data access utilities."""

from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path

BASE_FILENAMES = (
    "movies.csv",
    "film_actors.csv",
    "actor_awards.csv",
    "no_award_actors.csv",
)


def bundled_base_resource(file_name: str):
    """Return Traversable for bundled base data file."""
    return files("oscar_predictions.data.base").joinpath(file_name)


def bundled_config_resource(file_name: str):
    """Return Traversable for bundled config data file."""
    return files("oscar_predictions.data.config").joinpath(file_name)


def resolve_bundled_path(file_name: str) -> Path:
    """
    Resolve a packaged resource to a real filesystem Path.
    The caller should use this for short-lived operations.
    """
    resource = bundled_base_resource(file_name)
    with as_file(resource) as p:
        return Path(p)

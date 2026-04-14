# Phase 1 parity contract

Refactors under this contract must **not** change user-visible behavior of the pipeline unless explicitly versioned and documented.

## CSV outputs

- **Column names and order** for every writer must match pre-refactor behavior (see `oscar_predictions.oscar_scrape` constants and each script’s `DictWriter` field lists).
- **Default output paths** stay relative to the process working directory and keep the same basenames (`movies.csv`, `film_actors.csv`, etc.).

## Append vs overwrite

- **Append:** `scrape_movies`, `scrape_actors`, `scrape_actor_awards` (and their `run_*` equivalents).
- **Overwrite:** `award_show_counts`, `actor_year_award_matrix`, `film_actors_award_totals`, `join_movie_to_actor`.

## Semantics

- Award line parsing: `oscar_predictions.award_regex` (`CEREMONY_PATTERN`, `parse_ceremony`).
- Non-major ceremony bucketing: `oscar_predictions.award_groups.classify_group` and `GROUP_KEYS` order.
- Join keys: `movies.csv` `title` + `year` match `film_actors` / sums `film_title` + `year` (strip rules unchanged).

## CLI

- Root scripts remain supported: `python3 scrape_movies.py`, etc. (see [ENTRYPOINTS.md](ENTRYPOINTS.md)).
- Secondary: `python3 -m oscar_predictions.<module>`.
- Browser visibility:
  - `scrape_movies`: default windowed; `--headless` runs headless; `--headed` is an explicit alias for windowed (mutually exclusive with `--headless`).
  - `scrape_actors` / `scrape_actor_awards`: default headless; `--headed` shows window; `--headless` is an explicit alias for headless (mutually exclusive with `--headed`).

## Verification

- Run `python3 -m unittest discover -s tests -v` from the repo root (non-network).
- After edits, spot-check `--help` for each entrypoint and one full offline pipeline run on fixture data if possible.

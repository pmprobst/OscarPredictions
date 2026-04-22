# Architecture

This document explains the OscarPredictions data pipeline end to end. The main focus is the core modules that create and update the pipeline's CSV artifacts.

## How to read this page

Each module section follows the same format:
- Trigger: how it runs (CLI command or upstream module).
- Input: CSV/data files it reads.
- Process: key transformation or scraping behavior.
- Output: CSV/artifacts it writes or updates.

Read the modules in order to follow the full pipeline lifecycle from workspace initialization, through scraping and feature engineering, to modeling.

## Core Modules

### `oscar_predictions/workspace.py` (`DataWorkspace`)

- Trigger: used by `oscar init-data`, `oscar build-features`, `oscar reset`, `oscar check-updates`, and `oscar model`.
- Input:
  - Bundled package data from `oscar_predictions/data/base/`.
  - Bundled config `major_award_shows.txt` from `oscar_predictions/data/config/`.
- Process:
  - Resolves canonical workspace file paths.
  - Copies bundled base files into a workspace.
  - Deletes derived CSV outputs when a refresh is needed.
- Output:
  - Creates/overwrites `movies.csv`.
  - Creates/overwrites `film_actors.csv`.
  - Creates/overwrites `actor_awards.csv`.
  - Creates/overwrites `no_award_actors.csv`.
  - Creates/overwrites `major_award_shows.txt`.
  - Deletes (when requested): `actor_year_award_matrix.csv`, `film_actors_awards_sums_up_to_that_point.csv`, `movies_with_cast_award_totals.csv`, `award_show_counts.csv`.

### `oscar_predictions/reset_workspace.py`

- Trigger: CLI command `oscar reset`.
- Input:
  - `movies.csv`
  - `film_actors.csv`
  - `actor_awards.csv`
  - `no_award_actors.csv`
- Process:
  - Trims base CSV rows to `year <= cutoff_year` (default 2023).
  - Prunes `no_award_actors.csv` so it stays aligned with retained actor IDs.
  - Clears derived outputs and sync checkpoint state.
- Output:
  - Rewrites `movies.csv`, `film_actors.csv`, `actor_awards.csv`, `no_award_actors.csv`.
  - Deletes `actor_year_award_matrix.csv`, `film_actors_awards_sums_up_to_that_point.csv`, `movies_with_cast_award_totals.csv`, `award_show_counts.csv`.
  - Deletes `.oscar_sync_state.json`.

### `oscar_predictions/scrape_movies.py`

- Trigger:
  - Triggered by `oscar sync` and `oscar check-updates`.
  - Can also run as a standalone script.
- Input:
  - IMDb Oscars pages for nominee discovery.
  - Existing `movies.csv` and `film_actors.csv` (append/skip checks).
- Process:
  - Scrapes Best Picture nominee films and precursor/director attributes.
  - Optionally captures cast rows for each scraped film.
  - Skips rows already present by IMDb ID.
- Output:
  - Appends new rows to `movies.csv`.
  - Optionally appends cast rows to `film_actors.csv`.

### `oscar_predictions/scrape_actors.py`

- Trigger:
  - Triggered by `oscar sync` and `oscar check-updates`.
  - Can also run as a standalone script.
- Input:
  - `movies.csv`
  - Existing `film_actors.csv`
  - `no_award_actors.csv` (for prune/recheck logic)
  - IMDb film full-credits pages.
- Process:
  - Backfills or extends cast rows for movies missing cast coverage.
  - Supports year-scoped updates during refresh flows.
  - Removes actors from `no_award_actors.csv` when they should be rechecked.
- Output:
  - Appends/updates `film_actors.csv`.
  - Rewrites `no_award_actors.csv` when recheck pruning applies.

### `oscar_predictions/scrape_actor_awards.py`

- Trigger:
  - Triggered by `oscar sync` and `oscar check-updates`.
  - Can also run as a standalone script.
- Input:
  - `film_actors.csv`
  - Existing `actor_awards.csv`
  - Existing `no_award_actors.csv`
  - IMDb actor awards pages.
- Process:
  - Scrapes award history for actor IDs found in cast data.
  - Skips previously processed IDs unless explicitly rechecked.
  - Tracks actors with no award rows in a dedicated registry.
- Output:
  - Appends rows to `actor_awards.csv`.
  - Appends/updates `no_award_actors.csv`.

### `oscar_predictions/actor_year_award_matrix.py`

- Trigger:
  - Triggered by `oscar build-features`, `oscar check-updates`, and `oscar sync` derived stage.
  - Can also run as a standalone script.
- Input:
  - `actor_awards.csv`
  - `major_award_shows.txt`
- Process:
  - Normalizes actor-award rows into actor-year aggregates.
  - Separates major-award metrics using the configured major-show list.
- Output:
  - Writes `actor_year_award_matrix.csv`.

### `oscar_predictions/film_actors_award_totals.py`

- Trigger:
  - Triggered by `oscar build-features`, `oscar check-updates`, and `oscar sync` derived stage.
  - Can also run as a standalone script.
- Input:
  - `film_actors.csv`
  - `actor_year_award_matrix.csv`
- Process:
  - Calculates actor cumulative award totals up to each film year.
  - Produces per-movie cast totals for downstream joining.
- Output:
  - Writes `film_actors_awards_sums_up_to_that_point.csv`.

### `oscar_predictions/join_movie_to_actor.py`

- Trigger:
  - Triggered by `oscar build-features`, `oscar check-updates`, and `oscar sync` derived stage.
  - Can also run as a standalone script.
- Input:
  - `movies.csv`
  - `film_actors_awards_sums_up_to_that_point.csv`
- Process:
  - Joins cast-award totals onto each movie row.
  - Produces the model-ready movie-level feature table.
- Output:
  - Writes `movies_with_cast_award_totals.csv`.

### `oscar_predictions/award_show_counts.py`

- Trigger:
  - Triggered by `oscar sync --include-counts`.
  - Can also run as a standalone script.
- Input:
  - `actor_awards.csv`
- Process:
  - Aggregates total rows by award show.
  - Produces a compact counts artifact for inspection/reporting.
- Output:
  - Writes `award_show_counts.csv`.

### `oscar_predictions/features.py`

- Trigger:
  - CLI command `oscar build-features`.
  - Called by `oscar check-updates`.
- Input:
  - `actor_awards.csv`
  - `major_award_shows.txt`
  - `film_actors.csv`
  - `movies.csv`
- Process:
  - Executes the post-cleaning feature chain:
    1. `actor_year_award_matrix.py`
    2. `film_actors_award_totals.py`
    3. `join_movie_to_actor.py`
- Output:
  - Writes `actor_year_award_matrix.csv`.
  - Writes `film_actors_awards_sums_up_to_that_point.csv`.
  - Writes `movies_with_cast_award_totals.csv`.

### `oscar_predictions/updates.py`

- Trigger: CLI command `oscar check-updates`.
- Input:
  - `movies.csv` (detect existing years)
  - `film_actors.csv` (collect actor IDs for recheck by new year)
  - `actor_awards.csv`
  - `no_award_actors.csv`
  - IMDb nominee, credits, and actor-award pages
- Process:
  - Detects ceremony years missing from current `movies.csv`.
  - Deletes derived outputs before refresh.
  - Scrapes new-year movies, cast, and actor awards.
  - Rechecks newly nominated actors even if previously marked no-award.
  - Rebuilds post-cleaning feature outputs.
- Output:
  - Appends `movies.csv`, `film_actors.csv`, `actor_awards.csv`.
  - Appends/updates `no_award_actors.csv`.
  - Rewrites derived files: `actor_year_award_matrix.csv`, `film_actors_awards_sums_up_to_that_point.csv`, `movies_with_cast_award_totals.csv`.

### `oscar_predictions/sync.py`

- Trigger: CLI command `oscar sync`.
- Input:
  - `movies.csv`
  - `film_actors.csv`
  - `actor_awards.csv`
  - `no_award_actors.csv`
  - `major_award_shows.txt`
  - Existing `.oscar_sync_state.json` checkpoint state (if present)
- Process:
  - Plans and runs stage-by-stage incremental sync with checkpointing.
  - Runs scraping stages first, then rebuilds derived tables when upstream rows changed (or when forced).
  - Optionally adds award-show aggregation stage with `--include-counts`.
- Output:
  - Updates `movies.csv`, `film_actors.csv`, `actor_awards.csv`, `no_award_actors.csv`.
  - Writes/rewrites `actor_year_award_matrix.csv`, `film_actors_awards_sums_up_to_that_point.csv`, `movies_with_cast_award_totals.csv`.
  - Optionally writes `award_show_counts.csv`.
  - Writes/updates `.oscar_sync_state.json`.

### `oscar_predictions/modeling.py`

- Trigger: CLI command `oscar model`.
- Input:
  - `movies_with_cast_award_totals.csv`
- Process:
  - Cleans and encodes model features.
  - Trains and evaluates logistic-regression pipeline by grouped year split.
  - Generates per-year winner predictions and metrics.
- Output:
  - In-memory model report printed via CLI.
  - Optional artifact `--predictions-csv <path>` (user-defined CSV path).
  - Optional artifact `--report-json <path>` (JSON, not CSV).

### `movies_actors_eda.py` (optional analysis app)

- Trigger: standalone Streamlit run (`streamlit run movies_actors_eda.py`).
- Input:
  - `movies.csv`
- Process:
  - Provides interactive exploratory analysis and visual summaries.
- Output:
  - Browser-rendered dashboard (no required pipeline CSV output).

## CSV Artifact Coverage

- `movies.csv`: initialized by `workspace.py`; updated by `scrape_movies.py`, `updates.py`, `sync.py`; trimmed by `reset_workspace.py`.
- `film_actors.csv`: initialized by `workspace.py`; updated by `scrape_movies.py` (optional cast), `scrape_actors.py`, `updates.py`, `sync.py`; trimmed by `reset_workspace.py`.
- `actor_awards.csv`: initialized by `workspace.py`; updated by `scrape_actor_awards.py`, `updates.py`, `sync.py`; trimmed by `reset_workspace.py`.
- `no_award_actors.csv`: initialized by `workspace.py`; updated/pruned by `scrape_actors.py` and `scrape_actor_awards.py`; updated by `updates.py`, `sync.py`; trimmed by `reset_workspace.py`.
- `actor_year_award_matrix.csv`: generated by `actor_year_award_matrix.py` through `features.py`, `updates.py`, and `sync.py`; deleted by `workspace.py`/`reset_workspace.py` during refresh/reset.
- `film_actors_awards_sums_up_to_that_point.csv`: generated by `film_actors_award_totals.py` through `features.py`, `updates.py`, and `sync.py`; deleted by `workspace.py`/`reset_workspace.py`.
- `movies_with_cast_award_totals.csv`: generated by `join_movie_to_actor.py` through `features.py`, `updates.py`, and `sync.py`; deleted by `workspace.py`/`reset_workspace.py`; consumed by `modeling.py`.
- `award_show_counts.csv`: generated by `award_show_counts.py` when included in `sync.py`; deleted by `workspace.py`/`reset_workspace.py`.


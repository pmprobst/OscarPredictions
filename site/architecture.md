# Architecture

This document is a walkthrough of the OscarPredictions data pipeline, from an empty workspace all the way to a trained model. It is organized around the Python modules under `oscar_predictions/` that create and update the pipeline's CSV artifacts, and it describes how each one fits into the larger story.

The pipeline has a natural lifecycle: a workspace is initialized from bundled base data, IMDb is scraped to extend that data, post-cleaning features are derived from the resulting CSVs, and finally a model is trained on the feature table. The module sections below are ordered to follow that lifecycle, so reading them top to bottom traces a single run through the system. For every module, the prose explains when it runs, which files it reads, what it does to that data, and which CSV artifacts it produces or removes.

## Core Modules

### `oscar_predictions/workspace.py` (`DataWorkspace`)

`DataWorkspace` is the foundation layer that the other stages rely on. It is used by `oscar init-data`, `oscar build-features`, `oscar reset`, `oscar check-updates`, and `oscar model` to resolve canonical workspace file paths and to stage bundled package data from `oscar_predictions/data/base/` along with the bundled `major_award_shows.txt` config from `oscar_predictions/data/config/`.

When invoked, it copies the bundled base files into the active workspace, creating or overwriting `movies.csv`, `film_actors.csv`, `actor_awards.csv`, `no_award_actors.csv`, and `major_award_shows.txt`. When a refresh is requested, it also deletes the derived outputs so they can be rebuilt cleanly: `actor_year_award_matrix.csv`, `film_actors_awards_sums_up_to_that_point.csv`, `movies_with_cast_award_totals.csv`, and `award_show_counts.csv`.

### `oscar_predictions/reset_workspace.py`

This module backs the `oscar reset` CLI command and is used to roll the workspace back to a clean historical state. It reads the current `movies.csv`, `film_actors.csv`, `actor_awards.csv`, and `no_award_actors.csv` and trims them so that only rows with `year <= cutoff_year` (2023 by default) remain, pruning `no_award_actors.csv` down to the actor IDs that still appear after the cut.

The trimmed CSVs are written back in place, and all derived artifacts are removed so the next build starts from scratch: `actor_year_award_matrix.csv`, `film_actors_awards_sums_up_to_that_point.csv`, `movies_with_cast_award_totals.csv`, and `award_show_counts.csv` are deleted, along with the sync checkpoint file `.oscar_sync_state.json`.

### `oscar_predictions/scrape_movies.py`

`scrape_movies.py` is the first scraping stage. It is driven by `oscar sync` and `oscar check-updates`, but can also be run directly as a standalone script. It reads IMDb Oscars pages to discover Best Picture nominees and their precursor and director attributes, and consults the existing `movies.csv` and `film_actors.csv` so it can skip rows that already exist by IMDb ID.

The result is new rows appended to `movies.csv`, and, when cast capture is enabled during the scrape, corresponding rows appended to `film_actors.csv` as well.

### `oscar_predictions/scrape_actors.py`

Once films are known, `scrape_actors.py` ensures each of them has cast coverage. It runs from `oscar sync` and `oscar check-updates`, or as a standalone script. It reads `movies.csv` to find the films to process, the current `film_actors.csv` to detect which ones are missing cast rows, and `no_award_actors.csv` so it knows which actors are eligible for a recheck. The actual cast data is pulled from IMDb film full-credits pages.

This module backfills or extends cast rows for uncovered films and supports year-scoped updates during refresh flows. Its outputs are appended or updated rows in `film_actors.csv`, and a rewritten `no_award_actors.csv` whenever recheck pruning removes actors that should be reconsidered.

### `oscar_predictions/scrape_actor_awards.py`

With cast data in hand, `scrape_actor_awards.py` goes out to IMDb actor-award pages to collect each actor's award history. Like the other scrapers, it is triggered by `oscar sync` and `oscar check-updates` and can also run standalone. It reads `film_actors.csv` to discover the actor IDs to process, and consults the existing `actor_awards.csv` and `no_award_actors.csv` to skip IDs that have already been handled, unless a recheck is explicitly requested.

New award rows are appended to `actor_awards.csv`, while actors that turn out to have no award history are recorded in `no_award_actors.csv` so they are not repeatedly scraped on subsequent runs.

### `oscar_predictions/actor_year_award_matrix.py`

This is the first post-scraping feature stage. It runs as part of `oscar build-features`, `oscar check-updates`, and the derived stage of `oscar sync`, and it can also be invoked directly. It reads `actor_awards.csv` together with the configured list of major shows in `major_award_shows.txt`.

It normalizes the raw actor-award rows into actor-year aggregates, separating out metrics for the configured major awards. The output is a single artifact: `actor_year_award_matrix.csv`.

### `oscar_predictions/film_actors_award_totals.py`

Next in the derivation chain, `film_actors_award_totals.py` is triggered by `oscar build-features`, `oscar check-updates`, and the derived stage of `oscar sync`, and it can also be run as a standalone script. It reads `film_actors.csv` and the `actor_year_award_matrix.csv` produced upstream.

For each actor it computes cumulative award totals up to each film's year, then rolls those per-actor totals into per-movie cast totals ready for joining. The result is `film_actors_awards_sums_up_to_that_point.csv`.

### `oscar_predictions/join_movie_to_actor.py`

This is the final join step in the feature chain. It is called from `oscar build-features`, `oscar check-updates`, and the derived stage of `oscar sync`, and can also run on its own. It reads `movies.csv` and the cast-totals table `film_actors_awards_sums_up_to_that_point.csv`.

Joining these two tables produces the model-ready movie-level feature table, written as `movies_with_cast_award_totals.csv`.

### `oscar_predictions/award_show_counts.py`

`award_show_counts.py` is an optional reporting stage, run by `oscar sync --include-counts` or as a standalone script. It reads `actor_awards.csv` and aggregates the total number of rows by award show, producing a compact summary artifact, `award_show_counts.csv`, that is useful for inspection and reporting.

### `oscar_predictions/features.py`

`features.py` is the orchestration layer behind the `oscar build-features` CLI command and is also called by `oscar check-updates`. It pulls together the inputs consumed by the feature chain, `actor_awards.csv`, `major_award_shows.txt`, `film_actors.csv`, and `movies.csv`, and runs the post-cleaning stages in the correct order: first `actor_year_award_matrix.py`, then `film_actors_award_totals.py`, and finally `join_movie_to_actor.py`.

A successful run therefore rewrites the three derived tables in sequence: `actor_year_award_matrix.csv`, `film_actors_awards_sums_up_to_that_point.csv`, and `movies_with_cast_award_totals.csv`.

### `oscar_predictions/updates.py`

`updates.py` is the engine behind `oscar check-updates` and is responsible for incorporating newly available Oscar years into an existing workspace. It reads `movies.csv` to see which ceremony years are already present, `film_actors.csv` to find actor IDs that may need to be rechecked for a new year, along with `actor_awards.csv` and `no_award_actors.csv`, and it fetches new data from IMDb nominee, credits, and actor-award pages.

Once it has identified the missing years, it deletes the derived outputs so nothing stale is left around, scrapes movies, cast, and actor awards for those years, and rechecks newly nominated actors even if they had previously been marked as having no awards. It then rebuilds the post-cleaning feature tables. In practice this means appending to `movies.csv`, `film_actors.csv`, and `actor_awards.csv`, updating `no_award_actors.csv`, and rewriting `actor_year_award_matrix.csv`, `film_actors_awards_sums_up_to_that_point.csv`, and `movies_with_cast_award_totals.csv`.

### `oscar_predictions/sync.py`

`sync.py` implements the `oscar sync` command and is the most general-purpose refresh path. It reads `movies.csv`, `film_actors.csv`, `actor_awards.csv`, `no_award_actors.csv`, and `major_award_shows.txt`, and looks for an existing checkpoint in `.oscar_sync_state.json` if one is present.

Its job is to plan and run the pipeline stage by stage with checkpointing: the scraping stages run first, and then the derived tables are rebuilt whenever upstream rows have actually changed (or whenever a rebuild is forced). Passing `--include-counts` adds the award-show aggregation stage to the plan. Across these stages it updates `movies.csv`, `film_actors.csv`, `actor_awards.csv`, and `no_award_actors.csv`; writes or rewrites `actor_year_award_matrix.csv`, `film_actors_awards_sums_up_to_that_point.csv`, and `movies_with_cast_award_totals.csv`; optionally writes `award_show_counts.csv`; and updates `.oscar_sync_state.json` to reflect the new state of the workspace.

### `oscar_predictions/modeling.py`

`modeling.py` is the final consumer of the pipeline and is invoked through `oscar model`. It reads the joined feature table `movies_with_cast_award_totals.csv` produced by the earlier stages.

It cleans and encodes the model features, trains and evaluates a logistic-regression pipeline using a grouped year split, and generates per-year winner predictions along with evaluation metrics. By default the report is printed to the CLI, but users can request artifacts via `--predictions-csv <path>` to save predictions as CSV and `--report-json <path>` to save the report as JSON.

### `movies_actors_eda.py` (optional analysis app)

`movies_actors_eda.py` is an optional Streamlit application that sits alongside the main pipeline and is run directly with `streamlit run movies_actors_eda.py`. It reads `movies.csv` and presents interactive exploratory analysis and visual summaries in the browser. It does not produce any pipeline CSV outputs of its own; its deliverable is the rendered dashboard.

## CSV Artifact Coverage

`movies.csv` is seeded by `workspace.py` from the bundled base data. It is then extended by `scrape_movies.py` as new Best Picture nominees are discovered, and further updated through `updates.py` and `sync.py` as new ceremony years arrive. When the workspace is rolled back, `reset_workspace.py` trims it down to the cutoff year.

`film_actors.csv` is likewise seeded by `workspace.py`. It is grown by `scrape_movies.py` when cast capture is enabled, filled in more thoroughly by `scrape_actors.py`, and continues to be updated by `updates.py` and `sync.py`. `reset_workspace.py` trims it alongside the other base tables during a reset.

`actor_awards.csv` starts life from `workspace.py`, accumulates new rows through `scrape_actor_awards.py`, and is further appended to by `updates.py` and `sync.py`. A reset via `reset_workspace.py` trims it back to rows within the cutoff year.

`no_award_actors.csv` is initialized by `workspace.py` and then maintained as a side-effect of the scraping stages: `scrape_actors.py` and `scrape_actor_awards.py` both update or prune it, and `updates.py` and `sync.py` keep it current on their refresh paths. It is trimmed by `reset_workspace.py` so that only actors still referenced after the cut remain.

`actor_year_award_matrix.csv` is a derived artifact generated by `actor_year_award_matrix.py` whenever the feature chain runs, whether from `features.py`, `updates.py`, or `sync.py`. It is deleted by `workspace.py` or `reset_workspace.py` during a refresh or reset so that it can always be rebuilt cleanly.

`film_actors_awards_sums_up_to_that_point.csv` is produced by `film_actors_award_totals.py` through the same three orchestrators, `features.py`, `updates.py`, and `sync.py`, and is likewise deleted by `workspace.py` and `reset_workspace.py` when the workspace is refreshed or reset.

`movies_with_cast_award_totals.csv` is generated by `join_movie_to_actor.py` at the end of the feature chain, again via `features.py`, `updates.py`, or `sync.py`. It is deleted by `workspace.py` and `reset_workspace.py` during a refresh or reset, and it is the single table consumed by `modeling.py` at the end of the pipeline.

`award_show_counts.csv` is an optional reporting artifact generated by `award_show_counts.py` when it is included in a `sync.py` run via `--include-counts`, and it is deleted by `workspace.py` and `reset_workspace.py` during a refresh or reset.

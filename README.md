# OscarPredictions

OscarPredictions is now organized around one supported workflow:

- **Single command:** `python3 -m oscar_predictions sync`
- **Single implementation surface:** `oscar_predictions/`
- **Hard break from legacy root scripts/import shims**

## Quick start

1. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
playwright install chromium
```

2. Run the end-to-end incremental pipeline:

```bash
python3 -m oscar_predictions sync
```

3. Typical variants:

```bash
python3 -m oscar_predictions sync --year 2026
python3 -m oscar_predictions sync --dry-run
python3 -m oscar_predictions sync --rebuild-derived
python3 -m oscar_predictions sync --continue-on-error
```

## What `sync` does

`sync` orchestrates the full pipeline in order:

1. Movie discovery/update
2. Cast update
3. Actor awards update
4. Actor-year matrix rebuild (when upstream changed or forced)
5. Film-actor cumulative totals rebuild
6. Movie-level join rebuild
7. Optional award-show counts (`--include-counts`)

Checkpoint state is written to `.oscar_sync_state.json` by default.

## CLI reference

Run help:

```bash
python3 -m oscar_predictions sync --help
```

## Core files

- CLI and command dispatch: `oscar_predictions/cli.py`
- Orchestrator/planner: `oscar_predictions/sync.py`
- Unified config model: `oscar_predictions/config.py`
- Stage summaries/report types: `oscar_predictions/models.py`
- Pipeline stage modules: `oscar_predictions/*.py`

## Output files

Defaults remain:

- `movies.csv`
- `film_actors.csv`
- `actor_awards.csv`
- `no_award_actors.csv`
- `actor_year_award_matrix.csv`
- `film_actors_awards_sums_up_to_that_point.csv`
- `movies_with_cast_award_totals.csv`
- `award_show_counts.csv`

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Migration note (hard break)

The old direct script entrypoints (`python3 scrape_movies.py`, etc.) and top-level import shims were removed.
Use `python3 -m oscar_predictions sync` going forward.

# OscarPredictions

Installable package for Oscar data initialization, update checks, feature generation, and modeling.

## Install

Install from TestPyPI:

```bash
python3 -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  oscar-predictions
```

After install, use the `oscar` CLI.

## Commands

Workspace defaults:
- `init-data` defaults to current directory (`.`)
- `build-features`, `reset`, `check-updates`, `model`, and `sync` default to `./data`

### 1) Initialize bundled base data (through 2025)

```bash
oscar init-data
```

Optional examples:

```bash
# initialize a specific workspace
oscar init-data --workspace-dir ./data

# overwrite existing bundled base files
oscar init-data --workspace-dir ./data --overwrite
```

This copies bundled package data into the workspace:

- `movies.csv`
- `film_actors.csv`
- `actor_awards.csv`
- `no_award_actors.csv`
- `major_award_shows.txt`

### 2) Reset workspace to a cutoff year (e.g. re-test updates locally)

```bash
oscar reset
```

This rewrites **base** CSVs so only rows with `year` ≤ `--cutoff-year` (default **2023**) remain in `movies.csv`, `film_actors.csv`, and `actor_awards.csv`; prunes `no_award_actors.csv` to actors still present in those trimmed files; deletes post-cleaning outputs (`actor_year_award_matrix.csv`, `film_actors_awards_sums_up_to_that_point.csv`, `movies_with_cast_award_totals.csv`, `award_show_counts.csv`); and removes `.oscar_sync_state.json`.

Optional examples:

```bash
# preview changes without writing files
oscar reset --dry-run

# trim to a different cutoff year
oscar reset --cutoff-year 2021

# run reset in a specific workspace
oscar reset --workspace-dir ./data
```

To restore the **exact** files shipped in the package instead of trimming in place, use `oscar init-data --workspace-dir ./data --overwrite`. Optional modeling outputs (`--report-json`, `--predictions-csv`) are not removed; delete those paths manually if needed.

### 3) Build post-cleaning features

```bash
oscar build-features
```

Optional examples:

```bash
# run feature build in a specific workspace
oscar build-features --workspace-dir ./data
```

Produces:

- `actor_year_award_matrix.csv`
- `film_actors_awards_sums_up_to_that_point.csv`
- `movies_with_cast_award_totals.csv`

### 4) Check for new nominations and refresh

```bash
oscar check-updates
```

Behavior:

- finds unsynced new years,
- deletes post-cleaning outputs,
- scrapes new years,
- rechecks actors from newly nominated films even if they were in `no_award_actors.csv`,
- rebuilds post-cleaning outputs.

Optional examples:

```bash
# run in a specific workspace
oscar check-updates --workspace-dir ./data

# run browser visibly instead of headless
oscar check-updates --headed

# cap per-run scraping work
oscar check-updates --max-movies 5 --max-actors 200
```

### 5) Run modeling

```bash
oscar model
```

Optional examples:

```bash
# set split controls
oscar model --seed 42 --test-size 0.25

# write output artifacts
oscar model --report-json report.json --predictions-csv preds.csv

# run modeling against a specific workspace
oscar model --workspace-dir ./data
```

### 6) Run end-to-end sync

```bash
oscar sync
```

Optional examples:

```bash
# show planned stages without executing
oscar sync --dry-run

# sync a single ceremony year
oscar sync --year 2026

# run browser visibly
oscar sync --headed

# force later derived rebuilds and include counts
oscar sync --rebuild-derived --include-counts

# keep going after a stage failure
oscar sync --continue-on-error

# cap per-run scraping work
oscar sync --max-movies 5 --max-actors 200

# run sync in a specific workspace
oscar sync --workspace-dir ./data
```

## Development/testing

```bash
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
```

The project is licensed under the MIT License; see `LICENSE`.

## Package structure

- `oscar_predictions/cli.py` - command surface
- `oscar_predictions/workspace.py` - workspace paths and file lifecycle
- `oscar_predictions/features.py` - feature build chain
- `oscar_predictions/updates.py` - update detection + refresh flow
- `oscar_predictions/modeling.py` - production modeling pipeline
- `oscar_predictions/reset_workspace.py` - trim base CSVs to a year cutoff and clear derived outputs
- `oscar_predictions/data/` - bundled base data/config assets

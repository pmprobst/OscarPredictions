# OscarPredictions

Installable package for Oscar data initialization, update checks, feature generation, and modeling.

## Install

```bash
python3 -m pip install .
playwright install chromium
```

After install, use the `oscar` CLI.

## Commands

### 1) Initialize bundled base data (through 2023)

```bash
oscar init-data --workspace-dir ./data
```

This copies bundled package data into the workspace:

- `movies.csv`
- `film_actors.csv`
- `actor_awards.csv`
- `no_award_actors.csv`
- `major_award_shows.txt`

### 2) Build post-cleaning features

```bash
oscar build-features --workspace-dir ./data
```

Produces:

- `actor_year_award_matrix.csv`
- `film_actors_awards_sums_up_to_that_point.csv`
- `movies_with_cast_award_totals.csv`

### 3) Check for new nominations and refresh

```bash
oscar check-updates --workspace-dir ./data --headless
```

Behavior:

- finds unsynced new years,
- deletes post-cleaning outputs,
- scrapes new years,
- rechecks actors from newly nominated films even if they were in `no_award_actors.csv`,
- rebuilds post-cleaning outputs.

### 4) Run modeling

```bash
oscar model --workspace-dir ./data --seed 42 --test-size 0.25
```

Optional outputs:

```bash
oscar model --workspace-dir ./data --report-json report.json --predictions-csv preds.csv
```

## Development/testing

```bash
python3 -m unittest discover -s tests -v
```

## Package structure

- `oscar_predictions/cli.py` - command surface
- `oscar_predictions/workspace.py` - workspace paths and file lifecycle
- `oscar_predictions/features.py` - feature build chain
- `oscar_predictions/updates.py` - update detection + refresh flow
- `oscar_predictions/modeling.py` - production modeling pipeline
- `oscar_predictions/data/` - bundled base data/config assets

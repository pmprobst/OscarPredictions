# OscarPredictions

Installable package for Oscar data initialization, update checks, feature generation, and modeling.

## Install

Install from TestPyPI:

```bash
python3 -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  oscar-predictions==0.2.3
python3 -m playwright install chromium
```

From a git checkout:

```bash
python3 -m pip install ".[all]"
playwright install chromium
```

Optional dependency groups:

- **`[model]`** – pandas and scikit-learn (`oscar model`).
- **`[all]`** – currently the same as `model`.

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

### 2) Reset workspace to a cutoff year (e.g. re-test updates locally)

```bash
oscar reset --workspace-dir ./data
```

This rewrites **base** CSVs so only rows with `year` ≤ `--cutoff-year` (default **2023**) remain in `movies.csv`, `film_actors.csv`, and `actor_awards.csv`; prunes `no_award_actors.csv` to actors still present in those trimmed files; deletes post-cleaning outputs (`actor_year_award_matrix.csv`, `film_actors_awards_sums_up_to_that_point.csv`, `movies_with_cast_award_totals.csv`, `award_show_counts.csv`); and removes `.oscar_sync_state.json`.

Preview without changing files:

```bash
oscar reset --workspace-dir ./data --dry-run
```

To restore the **exact** files shipped in the package instead of trimming in place, use `oscar init-data --workspace-dir ./data --overwrite`. Optional modeling outputs (`--report-json`, `--predictions-csv`) are not removed; delete those paths manually if needed.

### 3) Build post-cleaning features

```bash
oscar build-features --workspace-dir ./data
```

Produces:

- `actor_year_award_matrix.csv`
- `film_actors_awards_sums_up_to_that_point.csv`
- `movies_with_cast_award_totals.csv`

### 4) Check for new nominations and refresh

```bash
oscar check-updates --workspace-dir ./data --headless
```

Behavior:

- finds unsynced new years,
- deletes post-cleaning outputs,
- scrapes new years,
- rechecks actors from newly nominated films even if they were in `no_award_actors.csv`,
- rebuilds post-cleaning outputs.

### 5) Run modeling

```bash
oscar model --workspace-dir ./data --seed 42 --test-size 0.25
```

Optional outputs:

```bash
oscar model --workspace-dir ./data --report-json report.json --predictions-csv preds.csv
```

## Development/testing

```bash
python3 -m pip install -e ".[all]"
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

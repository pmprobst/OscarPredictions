---
title: "Documentation"
---

# Oscar Predictions Package Documentation

## Overview

**oscar_predictions** is a Python package for scraping, processing, and modeling Oscar Best Picture nomination data from IMDB. It provides a full pipeline, from raw web scraping through feature engineering to logistic regression modeling.

This package provides:

- Web scraping tools for IMDB Oscar nominees, cast lists, and award histories
- Feature engineering functions for building modeling-ready datasets
- A logistic regression model for predicting Best Picture winners

## Installation

Install the package with the `all` extra (recommended), which includes scraping and modeling dependencies:

```bash
pip install "oscar-predictions[all]"
playwright install chromium
```

Optional dependency groups:

- `[scrape]` — Playwright only, for `sync`, `check-updates`, and scrape-related commands
- `[model]` — pandas and scikit-learn only, for `oscar model`
- `[all]` — both groups (recommended for most users)

## Package Structure

```
oscar_predictions/
├── cli.py                    # Command-line interface
├── workspace.py              # Workspace paths and file lifecycle
├── features.py               # Feature build chain
├── updates.py                # Update detection and refresh flow
├── modeling.py               # Production modeling pipeline
├── reset_workspace.py        # Trim base CSVs and clear derived outputs
├── data/                     # Bundled base data and config assets
└── __init__.py
```

## Modules and Functions

### `workspace.py`

Manages all file paths for a given working directory. All pipeline functions accept a `DataWorkspace` instance to locate their input and output files.

Example usage:

```python
from oscar_predictions.workspace import DataWorkspace

ws = DataWorkspace.from_path("./my_workspace")
ws.init_base_data()
```

`init_base_data()` copies the bundled base CSV files into the workspace directory. Pass `overwrite=True` to replace existing files.

### `sync.py`

Orchestrates the full end-to-end pipeline: scraping movies, cast, and actor awards, then rebuilding all derived feature tables. Supports checkpointing so interrupted runs resume where they left off.

Example usage:

```python
from oscar_predictions.sync import run_sync
from oscar_predictions.config import SyncConfig, sync_paths_from_workspace

paths = sync_paths_from_workspace("./my_workspace")
config = SyncConfig(paths=paths, headless=True, dry_run=False)
report = run_sync(config)

for stage in report.stage_summaries:
    print(stage.name, "→", "skipped" if stage.skipped else "ran")
```

### `features.py`

Generates derived feature tables from cleaned base data. Runs three steps: building the actor-year award matrix, computing per-film cast award totals, and joining those totals to the movies table.

Example usage:

```python
from oscar_predictions.features import run_build_features
from oscar_predictions.workspace import DataWorkspace

ws = DataWorkspace.from_path("./my_workspace")
result = run_build_features(ws)
print(result["join"])
```

### `modeling.py`

Trains a logistic regression model on the processed movie dataset and returns per-year predicted vs. actual Best Picture winners along with accuracy and ROC AUC metrics.

Example usage:

```python
from oscar_predictions.modeling import run_model
from oscar_predictions.workspace import DataWorkspace

ws = DataWorkspace.from_path("./my_workspace")
report = run_model(ws, seed=42, test_size=0.25)

print(f"Accuracy: {report['accuracy']:.2%}")
for year_result in report["yearly_results"]:
    print(year_result["year"], "→ Predicted:", year_result["predicted_winner"])
```

### `updates.py`

Checks IMDB for Oscar ceremony years not yet present in the workspace, scrapes any new nominees and their cast and award data, and rebuilds all derived feature tables.

Example usage:

```python
from oscar_predictions.updates import run_check_updates
from oscar_predictions.workspace import DataWorkspace

ws = DataWorkspace.from_path("./my_workspace")
result = run_check_updates(ws, headless=True, max_movies=None, max_actors=None)
print("New years found:", result["new_years"])
```

### `reset_workspace.py`

Trims the base CSV files to a cutoff year, prunes the no-award actor registry to match the remaining data, deletes all derived outputs, and removes the sync state file. Useful for reproducing results from a specific point in time.

Example usage:

```python
from oscar_predictions.reset_workspace import run_reset_workspace
from oscar_predictions.workspace import DataWorkspace

ws = DataWorkspace.from_path("./my_workspace")
run_reset_workspace(ws, cutoff_year=2022)
```

Pass `dry_run=True` to preview what would be removed without modifying any files.

## Data

The `data/` directory inside the package contains bundled CSV files covering Oscar Best Picture nominees from 1996 through 2023, including film metadata, cast lists, and actor award histories. These files are accessed internally using `importlib.resources` and copied into a user workspace via `init_base_data()`.

## Dependencies

Dependencies are split into optional groups:

- `[scrape]` — Playwright (required for any scraping commands)
- `[model]` — pandas, scikit-learn (required for `oscar model`)
- `[all]` — installs both groups

The package itself installs with no required third-party dependencies. See `pyproject.toml` for the full list.

## Example Workflow

```python
from oscar_predictions.workspace import DataWorkspace
from oscar_predictions.features import run_build_features
from oscar_predictions.modeling import run_model

ws = DataWorkspace.from_path("./my_workspace")
ws.init_base_data()

run_build_features(ws)

report = run_model(ws)
print(f"Accuracy: {report['accuracy']:.2%}")
```

## License

This project is licensed under the MIT License.

## Authors

Created by Annie Busath and Paul Probst as part of a Data Science project.

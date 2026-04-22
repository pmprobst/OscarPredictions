---
title: "Tutorial"
toc: true
---

# OscarPredictions Tutorial

This tutorial is a hands-on practice lab. It is written as Markdown with copy/paste code cells, not executable notebook cells.

## Prerequisites

- Python 3.9+ installed
- Internet access for package installation (and optional update/sync scraping)
- A shell where you can run CLI commands

## 1) Set up a practice workspace

Create and move into a workspace directory:

```bash
mkdir -p tutorial_workspace
cd tutorial_workspace
pwd
```

Checkpoint:
- Confirm the printed path exists on disk.

## 2) Install the package (TestPyPI)

Use the same install command from the README:

```bash
python3 -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  oscar-predictions
```

Practice:
- Re-run the command and confirm pip reports it as already installed.

## 3) Verify the CLI is available

```bash
oscar --help
```

If `oscar` is not found:

```bash
python3 -m oscar_predictions.cli --help
```

Checkpoint:
- You should see commands including `init-data`, `build-features`, `check-updates`, `model`, `reset`, and `sync`.

## 4) Initialize bundled base data

From your project root (replace the path if needed), initialize data into your workspace:

```bash
oscar init-data --workspace-dir ./tutorial_workspace
```

Check created files:

```bash
ls -1 ./tutorial_workspace
```

Practice:
- Try `--overwrite` and compare behavior.

```bash
oscar init-data --workspace-dir ./tutorial_workspace --overwrite
```

## 5) Build post-cleaning features

Generate derived feature tables:

```bash
oscar build-features --workspace-dir ./tutorial_workspace
```

Confirm expected outputs:

```bash
ls -1 ./tutorial_workspace | sed -n '/actor_year_award_matrix.csv/p;/film_actors_awards_sums_up_to_that_point.csv/p;/movies_with_cast_award_totals.csv/p'
```

Practice:
- Open `movies_with_cast_award_totals.csv` and identify at least three model features.

## 6) Run modeling

Run the model and write artifacts:

```bash
oscar model \
  --workspace-dir ./tutorial_workspace \
  --report-json ./tutorial_workspace/report.json \
  --predictions-csv ./tutorial_workspace/predictions.csv
```

Confirm artifacts:

```bash
ls -1 ./tutorial_workspace | sed -n '/report.json/p;/predictions.csv/p'
```

Practice:
- Re-run with a specific split:

```bash
oscar model --workspace-dir ./tutorial_workspace --seed 42 --test-size 0.25
```

## 7) Optional practice: reset, updates, sync

These are optional because update/sync can take longer and may require live scraping.

### Reset (safe local practice)

Preview reset:

```bash
oscar reset --workspace-dir ./tutorial_workspace --dry-run
```

Run a real reset:

```bash
oscar reset --workspace-dir ./tutorial_workspace --cutoff-year 2021
```

Rebuild features after reset:

```bash
oscar build-features --workspace-dir ./tutorial_workspace
```

### Check updates (networked scraping)

```bash
# oscar check-updates --workspace-dir ./tutorial_workspace
```

### End-to-end sync

Use dry run first:

```bash
oscar sync --workspace-dir ./tutorial_workspace --dry-run
```

Optional bounded sync:

```bash
# oscar sync --workspace-dir ./tutorial_workspace --max-movies 5 --max-actors 200
```

## Troubleshooting

- `oscar: command not found`: run `python3 -m oscar_predictions.cli --help` to verify install path, then reinstall in the active environment.
- Install fails on TestPyPI: retry with the exact `--index-url` and `--extra-index-url` flags.
- Permission/path issues: use a writable workspace path and rerun `init-data`.
- Slow update/sync runs: start with `--dry-run` or cap work with `--max-movies` and `--max-actors`.

## Next steps

- Read [Documentation](documentation.md) for architecture and module details.
- See [Technical Report](report.md) for methodology and findings.

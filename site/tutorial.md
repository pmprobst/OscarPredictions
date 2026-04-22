---
title: "Tutorial"
toc: true
---

This tutorial is a hands-on walkthrough for a reader who understands the purpose of OscarPredictions but has never used the package before. It is written as a readable article, with copy/paste code cells you can run in your own terminal. The cells are not executed by the site itself.

## What you'll build

OscarPredictions is a small Python toolkit that turns decades of Best Picture nominee data into a working prediction pipeline. By the end of this tutorial you will have:

- Installed the `oscar-predictions` package and verified its command-line tool.
- Created a "workspace" on your machine where data and model outputs live side by side.
- Loaded bundled historical data, built feature tables from it, and trained a model that estimates each nominee's probability of winning.
- Practiced the optional refresh commands used to add new ceremony years as they happen.

You do not need any prior modeling or scraping experience. You only need to follow the steps in order.

## How the package is organized

Everything is driven by a single command-line tool named `oscar`. You tell it which subcommand to run and which workspace folder to use. The subcommands you will meet in this tutorial are:

- `oscar init-data`: Sets up a new workspace by copying the historical base data that ships with the package into a folder you choose.
- `oscar build-features`: Transforms the base data into model-ready feature tables.
- `oscar model`: Trains and evaluates the prediction model using those feature tables, and optionally saves a report and per-film predictions.
- `oscar reset`: Rolls the workspace back to a specific cutoff year so you can practice updates or re-run the pipeline from an earlier state.
- `oscar check-updates`: After the bundled **1996–2025** snapshot, looks online for **2026 or later** ceremony years missing from your workspace and pulls them in.
- `oscar sync`: Runs the full end-to-end refresh (detect + scrape + rebuild features) in one step.

Think of `init-data` and `build-features` as the setup stages, `model` as the payoff, and `reset`, `check-updates`, and `sync` as maintenance tools for keeping a workspace current over time.

## Prerequisites

- Python 3.9+ installed
- Internet access for package installation (and optional update/sync scraping)
- A terminal: on **macOS or Linux**, use Terminal (bash or zsh). On **Windows**, use **PowerShell** (Windows Terminal is fine). Where steps differ, this tutorial shows both a **bash** block and a **PowerShell** block.

The `oscar …` commands are identical on every platform. Only creating folders, choosing your Python launcher, and listing files change between shells.

## 1) Set up a practice workspace

A "workspace" in OscarPredictions is just a folder on your computer. All CSV inputs, derived feature tables, and model outputs live there together, which keeps experiments tidy and reproducible. You will create an empty folder now, and in the next steps the `oscar` tool will fill it with data, features, and results.

Create and move into a workspace directory.

**macOS / Linux (bash or zsh):**

```bash
mkdir -p tutorial_workspace
cd tutorial_workspace
pwd
```

**Windows (PowerShell):**

```powershell
New-Item -ItemType Directory -Force tutorial_workspace | Out-Null
Set-Location tutorial_workspace
Get-Location
```

What this does:
- Creates a new empty folder called `tutorial_workspace` (if it does not already exist) and switches your shell into it.

What you should see:
- The printed path ends with `tutorial_workspace` (on Windows you may see a drive letter and backslashes; that is expected).

Checkpoint:
- Confirm the printed path exists on disk.

## 2) Install the package (TestPyPI)

OscarPredictions is published to TestPyPI. TestPyPI is a sandbox version of the official Python Package Index, so the install command tells `pip` to look there first and fall back to the real PyPI for any normal dependencies such as `pandas` and `scikit-learn`.

Use the same install command from the README.

**macOS / Linux (bash or zsh):**

```bash
python3 -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  oscar-predictions
```

**Windows (PowerShell):** use the same flags; line continuation uses a backtick. If `python3` is not found, try `python` or `py -3` instead of `python3`.

```powershell
python -m pip install `
  --index-url https://test.pypi.org/simple/ `
  --extra-index-url https://pypi.org/simple/ `
  oscar-predictions
```

What this does:
- Downloads and installs the `oscar-predictions` package, plus the scientific libraries it needs to build features and train the model.

What you should see:
- A "Successfully installed" line listing `oscar-predictions` and its dependencies.

Practice:
- Re-run the command and confirm pip reports it as already installed.

## 3) Verify the CLI is available

Installing the package registers a small launcher called `oscar` on your system's PATH. This is the only command you will use for the rest of the tutorial, so it is worth confirming that your shell can find it before moving on.

```bash
oscar --help
```

The same command works in PowerShell: `oscar --help`.

If `oscar` is not found, your environment may not have its scripts directory on PATH. You can always invoke the same tool through Python directly:

**macOS / Linux:**

```bash
python3 -m oscar_predictions.cli --help
```

**Windows (PowerShell):** if `python3` is not on your PATH, use `python` or `py -3`:

```powershell
python -m oscar_predictions.cli --help
```

What this does:
- Prints the top-level help text and lists the available subcommands.

What you should see:
- A help message listing commands including `init-data`, `build-features`, `check-updates`, `model`, `reset`, and `sync`.

Checkpoint:
- You should see commands including `init-data`, `build-features`, `check-updates`, `model`, `reset`, and `sync`.

## 4) Initialize bundled base data

The package ships with a curated historical dataset of Best Picture nominees, their cast, and prior award results. Before you can build features or train a model, that base data needs to be copied into your workspace so the rest of the pipeline has something to read.

From your project root (replace the path if needed), initialize data into your workspace. Forward slashes in `--workspace-dir` work in PowerShell too; you can also use a Windows path such as `.\tutorial_workspace` or `C:\Users\you\OscarPredictions\tutorial_workspace`.

```bash
oscar init-data --workspace-dir ./tutorial_workspace
```

What this does:
- Copies the bundled CSVs (`movies.csv`, `film_actors.csv`, `actor_awards.csv`, `no_award_actors.csv`) and the `major_award_shows.txt` config into your workspace.

Check created files:

**macOS / Linux:**

```bash
ls -1 ./tutorial_workspace
```

**Windows (PowerShell):**

```powershell
Get-ChildItem -Name .\tutorial_workspace
```

What you should see:
- At minimum: `movies.csv`, `film_actors.csv`, `actor_awards.csv`, `no_award_actors.csv`, and `major_award_shows.txt`.

Practice:
- Try `--overwrite` and compare behavior. Without it, `init-data` will not replace existing files, which is how you protect a workspace you have already customized. With it, the workspace is reset to the exact files that ship with the package.

```bash
oscar init-data --workspace-dir ./tutorial_workspace --overwrite
```

## 5) Build post-cleaning features

A machine learning model cannot read the raw scraped tables directly; it needs a single tidy table with one row per nominated film and numeric columns describing that film's precursor awards and its cast's prior accolades. The `build-features` command is what turns the raw CSVs into that model-ready table, along with two intermediate tables that make the transformation traceable.

Generate derived feature tables:

```bash
oscar build-features --workspace-dir ./tutorial_workspace
```

What this does:
- Aggregates awards by actor and year, rolls those totals up to each film's cast, and then joins them to the film-level records to produce the final modeling table.

Confirm expected outputs:

**macOS / Linux:**

```bash
ls -1 ./tutorial_workspace | sed -n '/actor_year_award_matrix.csv/p;/film_actors_awards_sums_up_to_that_point.csv/p;/movies_with_cast_award_totals.csv/p'
```

**Windows (PowerShell):**

```powershell
Get-ChildItem .\tutorial_workspace -Name | Where-Object {
  $_ -match 'actor_year_award_matrix\.csv|film_actors_awards_sums_up_to_that_point\.csv|movies_with_cast_award_totals\.csv'
}
```

What you should see:
- Three new files: `actor_year_award_matrix.csv`, `film_actors_awards_sums_up_to_that_point.csv`, and `movies_with_cast_award_totals.csv`. The last one is the table the model will train on.

Practice:
- Open `movies_with_cast_award_totals.csv` and identify at least three model features.

## 6) Run modeling

This is the payoff step. The `model` command loads the final feature table, trains a logistic regression, evaluates it on a held-out split, and reports how well it predicts the actual Best Picture winners. You can optionally ask it to save a structured report and a predictions CSV so you can inspect the results later.

Run the model and write artifacts.

**macOS / Linux (line continuation with `\`):**

```bash
oscar model \
  --workspace-dir ./tutorial_workspace \
  --report-json ./tutorial_workspace/report.json \
  --predictions-csv ./tutorial_workspace/predictions.csv
```

**Windows (PowerShell, line continuation with backtick):**

```powershell
oscar model `
  --workspace-dir ./tutorial_workspace `
  --report-json ./tutorial_workspace/report.json `
  --predictions-csv ./tutorial_workspace/predictions.csv
```

You can also run the same command as a single line on either platform (no line breaks).

What this does:
- Trains a logistic regression on `movies_with_cast_award_totals.csv`, prints evaluation metrics, writes the metrics to `report.json`, and writes one predicted probability per film-year to `predictions.csv`.

Confirm artifacts:

**macOS / Linux:**

```bash
ls -1 ./tutorial_workspace | sed -n '/report.json/p;/predictions.csv/p'
```

**Windows (PowerShell):**

```powershell
Get-ChildItem .\tutorial_workspace -Name | Where-Object { $_ -match '^report\.json$|^predictions\.csv$' }
```

What you should see:
- Both `report.json` and `predictions.csv` listed in your workspace.

Practice:
- Re-run with a specific split to see how accuracy changes:

```bash
oscar model --workspace-dir ./tutorial_workspace --seed 42 --test-size 0.25
```

## 7) Optional practice: reset, updates, sync

The remaining commands exist because Oscar data keeps changing: new ceremonies happen each year, and you will sometimes want to rewind your workspace to test an update flow from a clean starting point. These are optional for a first read-through because some of them reach out to the internet and can take longer than the earlier steps.

### Reset (safe local practice)

`oscar reset` trims your workspace's base CSVs so only rows up to a chosen year remain, and removes the derived feature tables. It is the easiest way to simulate "what if I only had data through year X?" without touching the bundled package files. A dry run shows what would change without writing anything, which is the safest way to explore the command for the first time.

Preview reset:

```bash
oscar reset --workspace-dir ./tutorial_workspace --dry-run
```

What this does:
- Prints the rows and files that would be modified or deleted, and then exits without changing anything.

Run a real reset:

```bash
oscar reset --workspace-dir ./tutorial_workspace --cutoff-year 2021
```

What this does:
- Rewrites `movies.csv`, `film_actors.csv`, and `actor_awards.csv` to drop rows past 2021, prunes `no_award_actors.csv` to actors that still appear, and deletes the derived feature tables.

Rebuild features after reset:

```bash
oscar build-features --workspace-dir ./tutorial_workspace
```

What this does:
- Regenerates the feature tables so you can train a model on the earlier data state.

### Check updates (networked scraping)

The package bundles historical Oscar Best Picture data from **1996 through 2025**. After `oscar init-data`, your workspace starts from that snapshot. **`oscar check-updates`** compares your workspace to what is available online and, when it finds newer ceremony years (**2026 or later**), downloads and merges that new data: nominees, cast, actor awards, and then rebuilt feature tables.

It is how you bring an existing workspace current when a new Oscars season appears in the wild. The command below is commented out because running it makes live network requests to IMDb. Remove the `#` only when you intend to run a long scrape.

::: {.callout-warning}
## ⚠️ ⚠️ Warning: long runtimes

**⚠️ `oscar check-updates` can take multiple hours per ceremony year** being added (scraping nominees, full cast lists, and award histories is slow and rate-sensitive). Plan for an unattended machine, a stable network, and consider using caps such as `--max-movies` and `--max-actors` if you only want a partial test run first.
:::

```bash
# oscar check-updates --workspace-dir ./tutorial_workspace
```

### End-to-end sync

`oscar sync` is the most complete refresh path. It plans each stage (scrape, derive, optional counts), checkpoints progress as it goes, and can limit per-run work so that a single command does not balloon into a long scrape. Starting with a dry run shows you the plan before any network calls are made.

Use dry run first:

```bash
oscar sync --workspace-dir ./tutorial_workspace --dry-run
```

What this does:
- Prints the stages `oscar sync` would run, in order, without executing them.

Optional bounded sync:

```bash
# oscar sync --workspace-dir ./tutorial_workspace --max-movies 5 --max-actors 200
```

What this does (if you uncomment it):
- Executes the sync plan but caps how many movies and actors will be scraped this run, so you can test the flow safely.

## Putting it all together

You now have a working OscarPredictions workspace on your machine. You used `init-data` to seed it with the bundled historical dataset, `build-features` to turn that data into a model-ready table, and `model` to produce predictions and metrics. You also saw how `reset` lets you rewind the workspace, and how `check-updates` and `sync` bring new ceremony years into the same pipeline with a single command.

From here, the practical mental model is:

- Run `build-features` whenever your base CSVs change.
- Run `model` whenever you want a fresh evaluation and predictions.
- Reach for `check-updates` or `sync` only when you want to bring in new data from outside your machine.

## Troubleshooting

- `oscar: command not found` (or not recognized in PowerShell): run `python3 -m oscar_predictions.cli --help` on macOS/Linux, or `python -m oscar_predictions.cli --help` / `py -3 -m oscar_predictions.cli --help` on Windows, to verify the install path; then reinstall in the active environment.
- Install fails on TestPyPI: retry with the exact `--index-url` and `--extra-index-url` flags.
- Permission/path issues: use a writable workspace path and rerun `init-data`.
- Slow update/sync runs: start with `--dry-run` or cap work with `--max-movies` and `--max-actors`.
- **Windows:** if only `py` works, use `py -3 -m pip install …` for installs and `py -3 -m oscar_predictions.cli …` instead of `python3`. Paths can use `\` or `/` in most `oscar` arguments.

## Next steps

- Read [Documentation](documentation.md) for architecture and module details.
- See [Technical Report](report.md) for methodology and findings.

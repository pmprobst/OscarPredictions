# OscarPredictions

Python tooling to scrape IMDb film and actor data, collect per-actor award history, and build **actor–year** feature tables for modeling (e.g. predicting film outcomes from cast award exposure).

---

## Python modules

| File | Purpose |
|------|-----------|
| [`oscar_scrape.py`](oscar_scrape.py) | Shared library: Playwright browser setup, IMDb parsing helpers, constants (`CSV_FILE`, `ACTOR_AWARDS_CSV_FILE`, `NO_AWARD_ACTORS_CSV_FILE`, field names), and core scraping routines used by the scrape scripts. |
| [`scrape_movies.py`](scrape_movies.py) | Scrapes movie listings into `movies.csv` (default path from `oscar_scrape`; schema in that module). |
| [`scrape_actors.py`](scrape_actors.py) | Scrapes cast into [`film_actors.csv`](film_actors.csv). For each **newly scraped** film, removes those cast members’ `nm` ids from `no_award_actors.csv` (unless `--skip-no-award-prune`) so `scrape_actor_awards.py` can recheck them. |
| [`scrape_actor_awards.py`](scrape_actor_awards.py) | For each unique actor in `film_actors.csv`, opens IMDb award pages and **appends** rows to [`actor_awards.csv`](actor_awards.csv) (nominations and wins). Uses Playwright. |
| [`award_regex.py`](award_regex.py) | Single definition of the IMDb award-line regex and `parse_ceremony()` to extract the **ceremony name** from the full `award` text. Shared by counting and matrix scripts. |
| [`award_groups.py`](award_groups.py) | Maps a ceremony string to a **fixed group key** (e.g. `us_regional_critics`, `television`) for aggregated columns. Edit `classify_group()` to override how a specific show is bucketed. |
| [`award_show_counts.py`](award_show_counts.py) | Reads `actor_awards.csv` only; counts rows per distinct ceremony; writes [`award_show_counts.csv`](award_show_counts.csv). |
| [`actor_year_award_matrix.py`](actor_year_award_matrix.py) | Reads `actor_awards.csv` only; builds one row per **(actor, year)** with `maj_*` columns for [major award shows](major_award_shows.txt) and `grp_*` columns for grouped non-major ceremonies (nomination and win **counts**). Writes [`actor_year_award_matrix.csv`](actor_year_award_matrix.csv). |
| [`film_actors_award_totals.py`](film_actors_award_totals.py) | Reads [`film_actors.csv`](film_actors.csv) and [`actor_year_award_matrix.csv`](actor_year_award_matrix.csv); for each film–cast row with film year **F**, appends cumulative `maj_*` / `grp_*` totals for that actor over all award years **≤ F** (no future-year awards). Writes [`film_actors_awards_sums_up_to_that_point.csv`](film_actors_awards_sums_up_to_that_point.csv). |
| [`join_movie_to_actor.py`](join_movie_to_actor.py) | Joins [`movies.csv`](movies.csv) to [`film_actors_awards_sums_up_to_that_point.csv`](film_actors_awards_sums_up_to_that_point.csv) on `year` + title; **sums** every `maj_*` / `grp_*` column across credited cast for one row per nominated film. Writes [`movies_with_cast_award_totals.csv`](movies_with_cast_award_totals.csv) by default. |

---

## Configuration and inputs

| File | Purpose |
|------|-----------|
| [`major_award_shows.txt`](major_award_shows.txt) | One **exact** IMDb ceremony name per line (as extracted by `award_regex`). Lines starting with `#` are ignored. These shows get dedicated `maj_*` columns in the actor–year matrix; all other ceremonies roll into `grp_*` groups via `award_groups.py`. |
| [`requirements.txt`](requirements.txt) | Python dependencies (Playwright for scraping). |
| [`.gitignore`](.gitignore) | Ignores virtualenv, bytecode, and local editor paths. |

---

## Data files (CSV)

Large CSVs are **outputs of scrapes** or **derived features**; treat paths as configurable in each script.

| File | Purpose |
|------|---------|
| `movies.csv` | Default output filename for `scrape_movies.py` (scraped movie records; may not be present until you run the scraper). |
| [`film_actors.csv`](film_actors.csv) | **Year, film title, actor name, actor IMDb URL** — links films to cast. Used as the driver list for `scrape_actor_awards.py`. |
| [`actor_awards.csv`](actor_awards.csv) | **Append-only** scrape of each actor’s IMDb awards: `actor_name`, `actor_imdb_url`, full `award` string, `year`, `outcome` (`won` / `nominated`). Source for all award analytics scripts. |
| `no_award_actors.csv` | Actors with no listed award lines after a successful scrape; used to skip repeat award scrapes. Rows for cast of **newly scraped** films are removed by `scrape_actors.py` so awards can be rechecked. |
| [`award_show_counts.csv`](award_show_counts.csv) | **Generated.** Distinct ceremony names and how often they appear in `actor_awards.csv`. |
| [`actor_year_award_matrix.csv`](actor_year_award_matrix.csv) | **Generated.** Wide actor–year table: keys plus `maj_*` / `grp_*` nomination and win counts for modeling or joins to `film_actors.csv`. |
| [`film_actors_awards_sums_up_to_that_point.csv`](film_actors_awards_sums_up_to_that_point.csv) | **Generated.** Same rows as `film_actors.csv` plus cumulative matrix columns through each film’s year (award years ≤ film year). |
| [`movies_with_cast_award_totals.csv`](movies_with_cast_award_totals.csv) | **Generated.** One row per `movies.csv` film: all movie columns plus `cast_row_count` and summed cast `maj_*` / `grp_*` totals (from `join_movie_to_actor.py`). |

---

## Typical workflow

1. Scrape or refresh **movies** and **film–actor** data (`scrape_movies.py`, `scrape_actors.py`). When `scrape_actors.py` adds cast for films not already in `film_actors.csv`, it prunes matching actors from `no_award_actors.csv` so the next awards pass can pick up new IMDb listings for that cast.
2. Run **`scrape_actor_awards.py`** to grow `actor_awards.csv` for unique cast members (and refresh `no_award_actors.csv` for anyone still without listed awards).
3. Optionally run **`award_show_counts.py`** to inspect ceremony frequencies and regex gaps.
4. Adjust **`major_award_shows.txt`** and **`award_groups.py`** as needed.
5. Run **`actor_year_award_matrix.py`** to produce the bounded-width feature table for joins.
6. Run **`film_actors_award_totals.py`** to attach cumulative award features to each film–cast row (through that film’s year).
7. Run **`join_movie_to_actor.py`** to build a single-row-per-film table with summed cast award exposure for modeling against `movies.csv`.

---

## Requirements

- Python 3 with dependencies from `requirements.txt`.
- Playwright browsers: after install, run `playwright install` (or `playwright install chromium`) for scraping scripts.

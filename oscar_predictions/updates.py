"""Update-check logic for discovering new Oscar years and refreshing derived outputs."""

from __future__ import annotations

import csv
from datetime import datetime, timezone

from oscar_predictions.features import run_build_features
from oscar_predictions.oscar_scrape import _imdb_browser_context, iter_best_picture_nominees, nm_id_from_profile_url
from oscar_predictions.scrape_actor_awards import run_scrape_actor_awards
from oscar_predictions.scrape_actors import run_scrape_actors
from oscar_predictions.scrape_movies import run_scrape_movies
from oscar_predictions.workspace import DataWorkspace


def _max_movie_year(movies_csv: str) -> int | None:
    try:
        with open(movies_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            years: list[int] = []
            for row in reader:
                raw = (row.get("year") or "").strip()
                try:
                    years.append(int(raw))
                except ValueError:
                    continue
        return max(years) if years else None
    except FileNotFoundError:
        return None


def _discover_new_nominee_years(existing_max_year: int | None, *, headless: bool) -> list[int]:
    from playwright.sync_api import sync_playwright

    start = (existing_max_year + 1) if existing_max_year is not None else 1996
    current_year = datetime.now(timezone.utc).year + 1
    discovered: list[int] = []
    with sync_playwright() as p:
        browser, context = _imdb_browser_context(p, headless=headless)
        try:
            for y in range(start, current_year + 1):
                gen = iter_best_picture_nominees(context, y, max_movies=1)
                first = next(gen, None)
                if first:
                    discovered.append(y)
        finally:
            context.close()
            browser.close()
    return discovered


def _collect_cast_nm_ids_for_year(cast_csv: str, year: int) -> set[str]:
    out: set[str] = set()
    with open(cast_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = (row.get("year") or "").strip()
            try:
                if int(raw) != year:
                    continue
            except ValueError:
                continue
            nm = nm_id_from_profile_url((row.get("actor_imdb_url") or "").strip())
            if nm:
                out.add(nm)
    return out


def run_check_updates(workspace: DataWorkspace, *, headless: bool, max_movies: int | None, max_actors: int | None) -> dict:
    existing_max = _max_movie_year(str(workspace.movies))
    new_years = _discover_new_nominee_years(existing_max, headless=headless)
    if not new_years:
        return {"new_years": [], "updated": False, "removed_derived": [], "features": {}}

    removed_derived = workspace.delete_derived_outputs()

    movie_summaries: list[dict] = []
    cast_summaries: list[dict] = []
    awards_summaries: list[dict] = []
    for y in new_years:
        movie_summaries.append(
            run_scrape_movies(
                year=y,
                headless=headless,
                csv_path=str(workspace.movies),
                csv_cast=str(workspace.cast),
                no_cast=False,
                max_movies=max_movies,
            )
        )
        cast_summaries.append(
            run_scrape_actors(
                movies=str(workspace.movies),
                year=y,
                headless=headless,
                csv_cast=str(workspace.cast),
                max_movies=max_movies,
                no_award_csv=str(workspace.no_award_actors),
                skip_no_award_prune=False,
            )
        )
        recheck_nm_ids = _collect_cast_nm_ids_for_year(str(workspace.cast), y)
        awards_summaries.append(
            run_scrape_actor_awards(
                input_path=str(workspace.cast),
                output_path=str(workspace.actor_awards),
                no_award_output=str(workspace.no_award_actors),
                force_rescrape=False,
                force_recheck_nm_ids=recheck_nm_ids,
                headless=headless,
                max_actors=max_actors,
            )
        )

    features = run_build_features(workspace)
    return {
        "new_years": new_years,
        "updated": True,
        "removed_derived": removed_derived,
        "movies": movie_summaries,
        "cast": cast_summaries,
        "awards": awards_summaries,
        "features": features,
    }

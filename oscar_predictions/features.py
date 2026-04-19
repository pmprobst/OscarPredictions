"""Post-cleaning feature generation command helpers."""

from __future__ import annotations

from oscar_predictions.actor_year_award_matrix import run_actor_year_award_matrix
from oscar_predictions.film_actors_award_totals import run_film_actors_award_totals
from oscar_predictions.join_movie_to_actor import run_join_movie_to_actor
from oscar_predictions.workspace import DataWorkspace


def run_build_features(workspace: DataWorkspace) -> dict[str, dict]:
    matrix = run_actor_year_award_matrix(
        input_path=str(workspace.actor_awards),
        output_path=str(workspace.actor_year_matrix),
        major_list=str(workspace.major_list),
        max_rows=None,
    )
    totals = run_film_actors_award_totals(
        film_actors=str(workspace.cast),
        matrix=str(workspace.actor_year_matrix),
        output=str(workspace.film_actor_totals),
        max_rows=None,
    )
    joined = run_join_movie_to_actor(
        movies=str(workspace.movies),
        film_actors_sums=str(workspace.film_actor_totals),
        output=str(workspace.movie_totals),
        inner=False,
        no_cast_count=False,
    )
    return {"matrix": matrix, "totals": totals, "join": joined}

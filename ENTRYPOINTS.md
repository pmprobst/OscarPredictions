# Entrypoints

Supported entrypoint:

- `python3 -m oscar_predictions sync`

## Examples

```bash
python3 -m oscar_predictions sync
python3 -m oscar_predictions sync --year 2026
python3 -m oscar_predictions sync --dry-run
python3 -m oscar_predictions sync --rebuild-derived
python3 -m oscar_predictions sync --continue-on-error
python3 -m oscar_predictions sync --include-counts
```

## Removed entrypoints (hard break)

The following legacy patterns are no longer supported:

- `python3 scrape_movies.py`
- `python3 scrape_actors.py`
- `python3 scrape_actor_awards.py`
- `python3 award_show_counts.py`
- `python3 actor_year_award_matrix.py`
- `python3 film_actors_award_totals.py`
- `python3 join_movie_to_actor.py`

Legacy top-level import shims were also removed. Import from `oscar_predictions.*` directly.

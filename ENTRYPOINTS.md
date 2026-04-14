# How to run the pipeline

## Canonical (recommended during transition)

Run the **root wrapper scripts** from the repository root (same as before the package layout):

```bash
python3 scrape_movies.py --help
python3 scrape_actors.py --help
python3 scrape_actor_awards.py --help
python3 award_show_counts.py --help
python3 actor_year_award_matrix.py --help
python3 film_actors_award_totals.py --help
python3 join_movie_to_actor.py --help
```

## Module execution (secondary)

With the repo root on `PYTHONPATH` (default when your shell cwd is the repo root):

```bash
python3 -m oscar_predictions.scrape_movies --help
python3 -m oscar_predictions.scrape_actors --help
python3 -m oscar_predictions.scrape_actor_awards --help
python3 -m oscar_predictions.award_show_counts --help
python3 -m oscar_predictions.actor_year_award_matrix --help
python3 -m oscar_predictions.film_actors_award_totals --help
python3 -m oscar_predictions.join_movie_to_actor --help
```

## Import compatibility

Legacy top-level module names still resolve to the package implementation:

- `import oscar_scrape` → `oscar_predictions.oscar_scrape`
- `import award_regex` → `oscar_predictions.award_regex`
- `import award_groups` → `oscar_predictions.award_groups`

## Programmatic use

Each pipeline module exposes `parse_args(argv=None)` and `run_*` functions; `main(argv=None)` wires argparse to `run_*`. Import from `oscar_predictions.<module>`.

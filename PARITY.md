# Package Data/Behavior Contract

## Supported command surface

- `oscar init-data`
- `oscar build-features`
- `oscar check-updates`
- `oscar model`
- `oscar sync`

## Data contracts

Bundled base data (wheel/sdist):

- `movies.csv`
- `film_actors.csv`
- `actor_awards.csv`
- `no_award_actors.csv`
- `major_award_shows.txt`

Generated (workspace):

- `actor_year_award_matrix.csv`
- `film_actors_awards_sums_up_to_that_point.csv`
- `movies_with_cast_award_totals.csv`
- optional `award_show_counts.csv`

## Semantic invariants

1. Base scraping stages append to base CSVs.
2. Post-cleaning stages overwrite derived outputs.
3. `check-updates` removes derived outputs before rebuilding when new years are discovered.
4. `check-updates` rechecks actors from newly nominated films even if they are in `no_award_actors.csv`.
5. Join/grouping/parsing behavior is unchanged from current package stage modules.

## Validation

```bash
python3 -m unittest discover -s tests -v
```

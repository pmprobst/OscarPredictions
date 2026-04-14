# Entrypoints

Preferred installed entrypoint:

- `oscar`

Module form (without installation):

- `python3 -m oscar_predictions`

## Commands

```bash
oscar init-data --workspace-dir ./data
oscar reset --workspace-dir ./data
oscar build-features --workspace-dir ./data
oscar check-updates --workspace-dir ./data --headless
oscar model --workspace-dir ./data
oscar sync --workspace-dir ./data
```

## Legacy status

Old root scripts (`scrape_movies.py`, etc.) and top-level shim imports remain unsupported.

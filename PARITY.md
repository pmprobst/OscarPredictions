# Parity Contract (Post-Aggressive Refactor)

This project intentionally changed interface shape (hard break), but preserves core data semantics.

## Interface changes (intentional)

- Single workflow command: `python3 -m oscar_predictions sync`.
- Legacy root scripts and top-level shim imports removed.

## Semantic invariants (must remain true)

1. CSV output schemas preserve expected column names/order for each stage output.
2. Scrape stages append; derived stages overwrite.
3. Join/grouping logic remains unchanged:
   - award parsing via `award_regex`
   - non-major classification via `award_groups`
   - movie/cast key matching logic stays equivalent
4. Default output basenames remain consistent unless overridden by CLI flags.

## Validation

- Unit and integration tests in `tests/`.
- Command:

```bash
python3 -m unittest discover -s tests -v
```

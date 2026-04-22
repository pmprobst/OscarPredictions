from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oscar_predictions.cli import main
from oscar_predictions.reset_workspace import run_reset_workspace
from oscar_predictions.workspace import DataWorkspace


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


class TestResetWorkspace(unittest.TestCase):
    def test_trims_year_columns_and_prunes_no_award(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = DataWorkspace.from_path(root)

            _write_csv(
                ws.movies,
                ["title", "url", "year"],
                [
                    {"title": "Old", "url": "http://x", "year": "2023"},
                    {"title": "New", "url": "http://y", "year": "2024"},
                ],
            )
            _write_csv(
                ws.cast,
                ["year", "film_title", "actor_name", "actor_imdb_url"],
                [
                    {"year": "2023", "film_title": "F", "actor_name": "A", "actor_imdb_url": "https://n/a"},
                    {"year": "2024", "film_title": "G", "actor_name": "B", "actor_imdb_url": "https://n/b"},
                ],
            )
            _write_csv(
                ws.actor_awards,
                ["actor_name", "actor_imdb_url", "award", "year", "outcome"],
                [
                    {
                        "actor_name": "A",
                        "actor_imdb_url": "https://n/a",
                        "award": "X",
                        "year": "2023",
                        "outcome": "won",
                    },
                    {
                        "actor_name": "B",
                        "actor_imdb_url": "https://n/b",
                        "award": "Y",
                        "year": "2024",
                        "outcome": "nominated",
                    },
                ],
            )
            _write_csv(
                ws.no_award_actors,
                ["actor_name", "actor_imdb_url"],
                [
                    {"actor_name": "Orphan", "actor_imdb_url": "https://n/c"},
                    {"actor_name": "A", "actor_imdb_url": "https://n/a"},
                ],
            )

            for p, name in (
                (ws.actor_year_matrix, "m"),
                (ws.film_actor_totals, "t"),
                (ws.movie_totals, "j"),
                (ws.award_show_counts, "c"),
            ):
                p.write_text(name, encoding="utf-8")
            ws.state_file.write_text('{"y": 1}', encoding="utf-8")

            report = run_reset_workspace(ws, cutoff_year=2023, dry_run=False)

            self.assertFalse(report["dry_run"])
            self.assertEqual(report["movies"]["kept_rows"], 1)
            self.assertEqual(report["movies"]["total_rows"], 2)
            self.assertEqual(report["film_actors"]["kept_rows"], 1)
            self.assertEqual(report["actor_awards"]["kept_rows"], 1)
            self.assertEqual(report["no_award_actors"]["kept_rows"], 1)
            self.assertEqual(len(report["derived_removed"]), 4)
            self.assertTrue(report["state_removed"])

            with ws.movies.open(encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["year"], "2023")

            with ws.no_award_actors.open(encoding="utf-8") as f:
                nar = list(csv.DictReader(f))
            self.assertEqual(len(nar), 1)
            self.assertEqual(nar[0]["actor_imdb_url"], "https://n/a")

            self.assertFalse(ws.actor_year_matrix.exists())
            self.assertFalse(ws.state_file.exists())

    def test_skips_bad_year_rows(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = DataWorkspace.from_path(td)
            _write_csv(
                ws.movies,
                ["title", "url", "year"],
                [
                    {"title": "Ok", "url": "u", "year": "2023"},
                    {"title": "Bad", "url": "v", "year": "nope"},
                ],
            )
            _write_csv(ws.cast, ["year", "film_title", "actor_name", "actor_imdb_url"], [])
            _write_csv(ws.actor_awards, ["actor_name", "actor_imdb_url", "award", "year", "outcome"], [])

            report = run_reset_workspace(ws, cutoff_year=2023, dry_run=False)
            self.assertEqual(report["movies"]["skipped_bad_year"], 1)
            self.assertEqual(report["movies"]["kept_rows"], 1)

    def test_dry_run_does_not_modify_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = DataWorkspace.from_path(td)
            _write_csv(
                ws.movies,
                ["title", "url", "year"],
                [{"title": "New", "url": "u", "year": "2024"}],
            )
            _write_csv(
                ws.cast,
                ["year", "film_title", "actor_name", "actor_imdb_url"],
                [{"year": "2024", "film_title": "G", "actor_name": "B", "actor_imdb_url": "https://n/b"}],
            )
            _write_csv(
                ws.actor_awards,
                ["actor_name", "actor_imdb_url", "award", "year", "outcome"],
                [
                    {
                        "actor_name": "B",
                        "actor_imdb_url": "https://n/b",
                        "award": "Y",
                        "year": "2024",
                        "outcome": "nominated",
                    },
                ],
            )
            _write_csv(
                ws.no_award_actors,
                ["actor_name", "actor_imdb_url"],
                [{"actor_name": "B", "actor_imdb_url": "https://n/b"}],
            )
            ws.actor_year_matrix.write_text("x", encoding="utf-8")
            before = ws.movies.read_text(encoding="utf-8")

            report = run_reset_workspace(ws, cutoff_year=2023, dry_run=True)

            self.assertTrue(report["dry_run"])
            self.assertEqual(ws.movies.read_text(encoding="utf-8"), before)
            self.assertEqual(len(report["derived_removed"]), 1)
            self.assertTrue(ws.actor_year_matrix.exists())

    @patch("oscar_predictions.cli.run_reset_workspace")
    def test_reset_cli_dispatch(self, m_reset) -> None:
        m_reset.return_value = {"dry_run": True, "cutoff_year": 2023}
        rc = main(["reset", "--workspace-dir", ".", "--dry-run"])
        self.assertEqual(rc, 0)
        m_reset.assert_called_once()
        kwargs = m_reset.call_args.kwargs
        self.assertTrue(kwargs["dry_run"])
        self.assertEqual(kwargs["cutoff_year"], 2023)


if __name__ == "__main__":
    unittest.main()

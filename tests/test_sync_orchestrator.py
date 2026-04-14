"""Integration-style tests for sync planner/orchestrator behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oscar_predictions.config import SyncConfig, SyncPaths
from oscar_predictions.sync import run_sync


class TestSyncOrchestrator(unittest.TestCase):
    def _config(self, root: Path, *, year: int | None = None, dry_run: bool = False) -> SyncConfig:
        return SyncConfig(
            paths=SyncPaths(
                movies=str(root / "movies.csv"),
                cast=str(root / "film_actors.csv"),
                actor_awards=str(root / "actor_awards.csv"),
                no_award_actors=str(root / "no_award_actors.csv"),
                actor_year_matrix=str(root / "actor_year_award_matrix.csv"),
                film_actor_totals=str(root / "film_actors_awards_sums_up_to_that_point.csv"),
                movie_totals=str(root / "movies_with_cast_award_totals.csv"),
                award_show_counts=str(root / "award_show_counts.csv"),
                major_list=str(root / "major_award_shows.txt"),
                state_file=str(root / ".sync_state.json"),
            ),
            year=year,
            headless=True,
            dry_run=dry_run,
            rebuild_derived=False,
            continue_on_error=False,
            include_counts=True,
            max_movies=None,
            max_actors=None,
        )

    def test_dry_run_marks_stages_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "movies.csv").write_text("title,url,year\n", encoding="utf-8")
            cfg = self._config(root, year=2025, dry_run=True)
            report = run_sync(cfg)
            self.assertTrue(report.dry_run)
            self.assertGreaterEqual(len(report.stage_summaries), 6)
            self.assertTrue(all(s.skipped for s in report.stage_summaries))

    @patch("oscar_predictions.sync.run_award_show_counts")
    @patch("oscar_predictions.sync.run_join_movie_to_actor")
    @patch("oscar_predictions.sync.run_film_actors_award_totals")
    @patch("oscar_predictions.sync.run_actor_year_award_matrix")
    @patch("oscar_predictions.sync.run_scrape_actor_awards")
    @patch("oscar_predictions.sync.run_scrape_actors")
    @patch("oscar_predictions.sync.run_scrape_movies")
    def test_skip_movie_scrape_when_year_exists(
        self,
        m_movies,
        m_actors,
        m_awards,
        m_matrix,
        m_totals,
        m_join,
        m_counts,
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "movies.csv").write_text("title,url,year\nFoo,http://x,2025\n", encoding="utf-8")
            (root / "major_award_shows.txt").write_text("Academy Awards, USA\n", encoding="utf-8")
            m_movies.return_value = {"rows_added": 0}
            m_actors.return_value = {"rows_added": 0}
            m_awards.return_value = {"rows_added": 0}
            m_matrix.return_value = {"rows_added": 0}
            m_totals.return_value = {"rows_added": 0}
            m_join.return_value = {"rows_added": 0}
            m_counts.return_value = {"rows_added": 0}

            cfg = self._config(root, year=2025, dry_run=False)
            report = run_sync(cfg)
            movie_stage = [s for s in report.stage_summaries if s.name == "scrape_movies"][0]
            self.assertTrue(movie_stage.skipped)
            self.assertEqual(movie_stage.details.get("reason"), "planner_skip")
            m_movies.assert_not_called()


if __name__ == "__main__":
    unittest.main()

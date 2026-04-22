from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oscar_predictions.updates import run_check_updates
from oscar_predictions.workspace import DataWorkspace


class TestUpdatesLogic(unittest.TestCase):
    @patch("oscar_predictions.updates.run_build_features")
    @patch("oscar_predictions.updates.run_scrape_actor_awards")
    @patch("oscar_predictions.updates.run_scrape_actors")
    @patch("oscar_predictions.updates.run_scrape_movies")
    @patch("oscar_predictions.updates._discover_new_nominee_years")
    def test_new_year_triggers_recheck_override(
        self,
        m_discover,
        m_movies,
        m_cast,
        m_awards,
        m_features,
    ) -> None:
        m_discover.return_value = [2025]
        m_movies.return_value = {"rows_added": 1}
        m_cast.return_value = {"rows_added": 1}
        m_awards.return_value = {"rows_added": 1}
        m_features.return_value = {"ok": True}

        with tempfile.TemporaryDirectory() as td:
            ws = DataWorkspace.from_path(td)
            ws.ensure_exists()
            ws.movies.write_text("title,url,year\nExisting,http://x,2024\n", encoding="utf-8")
            ws.cast.write_text(
                "year,film_title,actor_name,actor_imdb_url\n"
                "2025,Foo,Actor One,https://www.imdb.com/name/nm0000001/\n",
                encoding="utf-8",
            )
            ws.actor_awards.write_text("actor_name,actor_imdb_url,award,year,outcome\n", encoding="utf-8")
            ws.no_award_actors.write_text("actor_name,actor_imdb_url\n", encoding="utf-8")
            ws.major_list.write_text("Academy Awards, USA\n", encoding="utf-8")

            out = run_check_updates(ws, headless=True, max_movies=None, max_actors=None)
            self.assertTrue(out["updated"])
            self.assertEqual(out["new_years"], [2025])
            kwargs = m_awards.call_args.kwargs
            self.assertIn("force_recheck_nm_ids", kwargs)
            self.assertIn("nm0000001", kwargs["force_recheck_nm_ids"])

    @patch("oscar_predictions.updates.run_build_features")
    @patch("oscar_predictions.updates.run_scrape_actor_awards")
    @patch("oscar_predictions.updates.run_scrape_actors")
    @patch("oscar_predictions.updates.run_scrape_movies")
    @patch("oscar_predictions.updates._discover_new_nominee_years")
    def test_backfill_multiple_missing_years(
        self,
        m_discover,
        m_movies,
        m_cast,
        m_awards,
        m_features,
    ) -> None:
        m_discover.return_value = [2024, 2025, 2026]
        m_movies.return_value = {"rows_added": 1}
        m_cast.return_value = {"rows_added": 1}
        m_awards.return_value = {"rows_added": 1}
        m_features.return_value = {"ok": True}

        with tempfile.TemporaryDirectory() as td:
            ws = DataWorkspace.from_path(td)
            ws.ensure_exists()
            ws.movies.write_text("title,url,year\nLegacy,http://x,2023\n", encoding="utf-8")
            ws.cast.write_text(
                "year,film_title,actor_name,actor_imdb_url\n"
                "2024,F1,Actor One,https://www.imdb.com/name/nm0000001/\n"
                "2025,F2,Actor Two,https://www.imdb.com/name/nm0000002/\n"
                "2026,F3,Actor Three,https://www.imdb.com/name/nm0000003/\n",
                encoding="utf-8",
            )
            ws.actor_awards.write_text("actor_name,actor_imdb_url,award,year,outcome\n", encoding="utf-8")
            ws.no_award_actors.write_text("actor_name,actor_imdb_url\n", encoding="utf-8")
            ws.major_list.write_text("Academy Awards, USA\n", encoding="utf-8")

            out = run_check_updates(ws, headless=True, max_movies=None, max_actors=None)
            self.assertTrue(out["updated"])
            self.assertEqual(out["new_years"], [2024, 2025, 2026])
            self.assertEqual(m_movies.call_count, 3)
            self.assertEqual(m_cast.call_count, 3)
            self.assertEqual(m_awards.call_count, 3)
            self.assertEqual(m_features.call_count, 1)
            self.assertEqual([c.kwargs["year"] for c in m_movies.call_args_list], [2024, 2025, 2026])

    @patch("oscar_predictions.updates.run_build_features")
    @patch("oscar_predictions.updates.run_scrape_actor_awards")
    @patch("oscar_predictions.updates.run_scrape_actors")
    @patch("oscar_predictions.updates.run_scrape_movies")
    @patch("oscar_predictions.updates._discover_new_nominee_years")
    def test_sparse_gap_years_processed_exactly(
        self,
        m_discover,
        m_movies,
        m_cast,
        m_awards,
        m_features,
    ) -> None:
        m_discover.return_value = [2024, 2026]
        m_movies.return_value = {"rows_added": 1}
        m_cast.return_value = {"rows_added": 1}
        m_awards.return_value = {"rows_added": 1}
        m_features.return_value = {"ok": True}

        with tempfile.TemporaryDirectory() as td:
            ws = DataWorkspace.from_path(td)
            ws.ensure_exists()
            ws.movies.write_text("title,url,year\nLegacy,http://x,2023\n", encoding="utf-8")
            ws.cast.write_text(
                "year,film_title,actor_name,actor_imdb_url\n"
                "2024,F1,Actor One,https://www.imdb.com/name/nm0000001/\n"
                "2026,F3,Actor Three,https://www.imdb.com/name/nm0000003/\n",
                encoding="utf-8",
            )
            ws.actor_awards.write_text("actor_name,actor_imdb_url,award,year,outcome\n", encoding="utf-8")
            ws.no_award_actors.write_text("actor_name,actor_imdb_url\n", encoding="utf-8")
            ws.major_list.write_text("Academy Awards, USA\n", encoding="utf-8")

            out = run_check_updates(ws, headless=True, max_movies=None, max_actors=None)
            self.assertTrue(out["updated"])
            self.assertEqual(out["new_years"], [2024, 2026])
            self.assertEqual([c.kwargs["year"] for c in m_movies.call_args_list], [2024, 2026])

    @patch("oscar_predictions.updates.run_build_features")
    @patch("oscar_predictions.updates.run_scrape_actor_awards")
    @patch("oscar_predictions.updates.run_scrape_actors")
    @patch("oscar_predictions.updates.run_scrape_movies")
    @patch("oscar_predictions.updates._discover_new_nominee_years")
    def test_no_discovery_exits_without_side_effects(
        self,
        m_discover,
        m_movies,
        m_cast,
        m_awards,
        m_features,
    ) -> None:
        m_discover.return_value = []

        with tempfile.TemporaryDirectory() as td:
            ws = DataWorkspace.from_path(td)
            ws.ensure_exists()
            ws.movies.write_text("title,url,year\nLegacy,http://x,2023\n", encoding="utf-8")
            ws.cast.write_text("year,film_title,actor_name,actor_imdb_url\n", encoding="utf-8")
            ws.actor_awards.write_text("actor_name,actor_imdb_url,award,year,outcome\n", encoding="utf-8")
            ws.no_award_actors.write_text("actor_name,actor_imdb_url\n", encoding="utf-8")
            ws.major_list.write_text("Academy Awards, USA\n", encoding="utf-8")

            out = run_check_updates(ws, headless=True, max_movies=None, max_actors=None)
            self.assertFalse(out["updated"])
            self.assertEqual(out["new_years"], [])
            m_movies.assert_not_called()
            m_cast.assert_not_called()
            m_awards.assert_not_called()
            m_features.assert_not_called()


if __name__ == "__main__":
    unittest.main()

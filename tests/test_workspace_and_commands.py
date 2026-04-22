from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oscar_predictions.cli import main
from oscar_predictions.workspace import DataWorkspace


class TestWorkspaceAndCommands(unittest.TestCase):
    def test_init_data_materializes_base_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = DataWorkspace.from_path(td)
            result = ws.init_base_data(overwrite=False)
            self.assertGreaterEqual(result["copied"], 5)
            self.assertIn("copied_files", result)
            self.assertIn("skipped_files", result)
            self.assertTrue(ws.movies.exists())
            self.assertTrue(ws.cast.exists())
            self.assertTrue(ws.actor_awards.exists())
            self.assertTrue(ws.no_award_actors.exists())
            self.assertTrue(ws.major_list.exists())

    def test_init_data_cli_output_is_human_readable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["init-data", "--workspace-dir", td, "--overwrite"])
            self.assertEqual(rc, 0)
            out = buf.getvalue()
            self.assertIn("Initialized workspace", out)
            self.assertIn("Downloaded files:", out)
            self.assertIn("movies.csv", out)
            self.assertIn("Bundled base data covers ceremony years through 2025.", out)

    @patch("oscar_predictions.cli.run_build_features")
    def test_build_features_command_dispatch(self, m_build) -> None:
        m_build.return_value = {"ok": True}
        rc = main(["build-features", "--workspace-dir", "."])
        self.assertEqual(rc, 0)
        m_build.assert_called_once()

    @patch("oscar_predictions.cli.run_check_updates")
    def test_check_updates_command_dispatch(self, m_updates) -> None:
        m_updates.return_value = {"updated": False, "new_years": []}
        rc = main(["check-updates", "--workspace-dir", ".", "--headless"])
        self.assertEqual(rc, 0)
        m_updates.assert_called_once()


if __name__ == "__main__":
    unittest.main()

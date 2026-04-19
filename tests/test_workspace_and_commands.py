from __future__ import annotations

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
            self.assertTrue(ws.movies.exists())
            self.assertTrue(ws.cast.exists())
            self.assertTrue(ws.actor_awards.exists())
            self.assertTrue(ws.no_award_actors.exists())
            self.assertTrue(ws.major_list.exists())

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

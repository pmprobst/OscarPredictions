from __future__ import annotations

import contextlib
import io
import json
import importlib.util
import tempfile
import unittest
from pathlib import Path

from oscar_predictions.cli import main
from oscar_predictions.modeling import run_model
from oscar_predictions.workspace import DataWorkspace


class TestModelingCommand(unittest.TestCase):
    @unittest.skipUnless(
        importlib.util.find_spec("pandas") and importlib.util.find_spec("sklearn"),
        "pandas/sklearn not installed",
    )
    def test_run_model_outputs_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = DataWorkspace.from_path(td)
            ws.ensure_exists()
            ws.movie_totals.write_text(
                "title,url,year,oscar_win,feat1,feat2\n"
                "A,http://a,2020,0,1,0\n"
                "B,http://b,2020,1,2,1\n"
                "C,http://c,2021,0,1,1\n"
                "D,http://d,2021,1,3,2\n",
                encoding="utf-8",
            )
            report_path = Path(td) / "report.json"
            pred_path = Path(td) / "preds.csv"
            rep = run_model(
                ws,
                seed=7,
                test_size=0.5,
                report_path=str(report_path),
                predictions_path=str(pred_path),
            )
            self.assertIn("accuracy", rep)
            self.assertIn("yearly_results", rep)
            self.assertGreaterEqual(len(rep["yearly_results"]), 1)
            first_year = rep["yearly_results"][0]
            self.assertIn("predicted_winner", first_year)
            self.assertIn("actual_winner", first_year)
            self.assertIn("nominees", first_year)
            self.assertTrue(report_path.exists())
            self.assertTrue(pred_path.exists())
            loaded = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertIn("features", loaded)
            self.assertIn("yearly_results", loaded)

    @unittest.skipUnless(
        importlib.util.find_spec("pandas") and importlib.util.find_spec("sklearn"),
        "pandas/sklearn not installed",
    )
    def test_model_command_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = DataWorkspace.from_path(td)
            ws.ensure_exists()
            ws.movie_totals.write_text(
                "title,url,year,oscar_win,feat1,feat2\n"
                "A,http://a,2020,0,1,0\n"
                "B,http://b,2020,1,2,1\n"
                "C,http://c,2021,0,1,1\n"
                "D,http://d,2021,1,3,2\n",
                encoding="utf-8",
            )
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["model", "--workspace-dir", str(ws.root), "--seed", "1", "--test-size", "0.5"])
            self.assertEqual(rc, 0)
            out = buf.getvalue()
            self.assertIn("Year ", out)
            self.assertIn("Predicted winner:", out)
            self.assertIn("Actual winner:", out)
            self.assertNotIn("model metrics:", out)


if __name__ == "__main__":
    unittest.main()

"""Parity-focused unit tests (no Playwright)."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from oscar_predictions.award_regex import parse_ceremony
from oscar_predictions.csvutil import (
    load_nm_ids_from_actor_url_column,
    missing_required_columns,
    open_append_csv_writer,
)


class TestRegexParity(unittest.TestCase):
    def test_parse_ceremony_nominee(self) -> None:
        s = "Academy Awards, USA — 2020 Nominee Some Category"
        self.assertEqual(parse_ceremony(s), "Academy Awards, USA")

    def test_parse_ceremony_winner(self) -> None:
        s = "Golden Globes, USA — 2019 Winner Best Actor"
        self.assertEqual(parse_ceremony(s), "Golden Globes, USA")

    def test_parse_ceremony_no_match(self) -> None:
        self.assertIsNone(parse_ceremony("not an imdb style line"))


class TestCsvUtil(unittest.TestCase):
    def test_missing_required_columns(self) -> None:
        self.assertEqual(
            missing_required_columns(["year", "title"], {"year", "url"}),
            ["url"],
        )
        self.assertEqual(missing_required_columns(None, {"a"}), ["a"])

    def test_open_append_csv_writer_writes_header_once(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.csv"
            f, w = open_append_csv_writer(p, ["a", "b"])
            try:
                w.writerow({"a": "1", "b": "2"})
            finally:
                f.close()
            text = p.read_text(encoding="utf-8")
            self.assertIn("a,b", text.splitlines()[0])
            f2, w2 = open_append_csv_writer(p, ["a", "b"])
            try:
                w2.writerow({"a": "3", "b": "4"})
            finally:
                f2.close()
            lines = p.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], "a,b")
            self.assertEqual(len(lines), 3)

    def test_load_nm_ids(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.csv"
            p.write_text(
                "actor_name,actor_imdb_url\n"
                "A,https://www.imdb.com/name/nm0000001/\n"
                "B,https://www.imdb.com/name/nm0000001/extra\n",
                encoding="utf-8",
            )
            ids = load_nm_ids_from_actor_url_column(p)
            self.assertEqual(ids, {"nm0000001"})


if __name__ == "__main__":
    unittest.main()

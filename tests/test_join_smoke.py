"""Smoke test for join_movie_to_actor run API."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from oscar_predictions.join_movie_to_actor import run_join_movie_to_actor


class TestJoinSmoke(unittest.TestCase):
    def test_left_join_zeros(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            movies = td_path / "movies.csv"
            sums = td_path / "sums.csv"
            out = td_path / "out.csv"
            movies.write_text("title,url,year\nFoo,http://x,2020\n", encoding="utf-8")
            sums.write_text(
                "year,film_title,actor_name,actor_imdb_url,grp_other_noms\n"
                "2020,Foo,A,https://www.imdb.com/name/nm1/,2\n",
                encoding="utf-8",
            )
            run_join_movie_to_actor(movies=str(movies), film_actors_sums=str(sums), output=str(out))
            with out.open(encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["title"], "Foo")
            self.assertEqual(rows[0]["cast_row_count"], "1")
            self.assertEqual(rows[0]["grp_other_noms"], "2")


if __name__ == "__main__":
    unittest.main()

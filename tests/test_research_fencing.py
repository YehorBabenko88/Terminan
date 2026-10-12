import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from terminan.data import research


class ResearchFencingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.temp.name, "research.sqlite")
        self.con = sqlite3.connect(self.path)
        self.con.execute("""CREATE TABLE research_results (
            run_id TEXT, symbol TEXT, strategy_id TEXT, strategy_version TEXT,
            created_at REAL, metrics TEXT, job_id TEXT,
            lease_token INTEGER, node_generation INTEGER)""")
        self.con.executemany(
            "INSERT INTO research_results VALUES (?,?,?,?,?,?,?,?,?)",
            [
                ("run1", "BTCUSDT", "s", "v1", 100, json.dumps({"net_pnl": 4}), None, 0, 0),
                ("run2", "BTCUSDT", "s", "v2", 200, json.dumps({"net_pnl": -2}), "job2", 7, 3),
            ],
        )
        self.con.commit()
        self.con.close()
        self.env = patch.dict(os.environ, {"TERMINAN_RESULTS_DB": self.path})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_fencing_presence_is_not_authority(self):
        rows = research("BTCUSDT")
        self.assertEqual(rows[0]["fencing"]["state"], "PRESENT_UNVERIFIED")
        self.assertTrue(rows[0]["fencing"]["lease_token_present"])
            self.assertNotIn("lease_token", rows[0]["fencing"])
        self.assertEqual(rows[0]["publication_authority"], "UNVERIFIED")
        self.assertEqual(rows[1]["fencing"]["state"], "LEGACY_UNFENCED")

    def test_bad_limit_rejected(self):
        with self.assertRaises(ValueError):
            research("BTCUSDT", 0)
        with self.assertRaises(ValueError):
            research("BTCUSDT", True)


if __name__ == "__main__":
    unittest.main()

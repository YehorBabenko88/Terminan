import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from terminan.data import research


class ResearchAdapterSafetyTests(unittest.TestCase):
    def test_no_fencing_token_leak_and_bad_metrics_isolated(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "results.sqlite")
            con = sqlite3.connect(path)
            con.execute("""CREATE TABLE research_results(
                run_id TEXT,symbol TEXT,strategy_id TEXT,strategy_version TEXT,
                created_at REAL,metrics TEXT,job_id TEXT,lease_token INTEGER,node_generation INTEGER)""")
            con.execute("INSERT INTO research_results VALUES (?,?,?,?,?,?,?,?,?)",
                        ("run1", "BTCUSDT", "strategy", "v1", 1.0,
                         '{"profit_factor":2}', "job1", 123456789, 5))
            con.execute("INSERT INTO research_results VALUES (?,?,?,?,?,?,?,?,?)",
                        ("run2", "BTCUSDT", "strategy", "v1", 2.0,
                         "{invalid", "job2", 987654321, 5))
            con.commit()
            con.close()
            with patch.dict(os.environ, {"TERMINAN_RESULTS_DB": path}):
                rows = research("BTCUSDT")
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["metrics_state"], "INVALID_METRICS")
            self.assertEqual(rows[0]["metrics"], {})
            self.assertEqual(rows[1]["metrics_state"], "PARSED")
            self.assertNotIn(chr(34) + "lease_token" + chr(34) + ":", json.dumps(rows))
            self.assertNotIn("123456789", json.dumps(rows))
            self.assertNotIn("987654321", json.dumps(rows))
            self.assertEqual(rows[0]["publication_authority"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()

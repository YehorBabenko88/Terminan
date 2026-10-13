import unittest
from unittest.mock import patch
from terminan.source_health import source_health


class SourceHealthTests(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_unconfigured_never_claims_live(self):
        health = source_health()
        self.assertEqual(health["mode"], "READ_ONLY")
        self.assertFalse(health["trading_enabled"])
        self.assertEqual(health["sources"]["cluster_grid"]["state"], "NOT_CONFIGURED")
        self.assertEqual(health["sources"]["cluster_grid"]["l2"], "NOT_EXPOSED")

    @patch.dict("os.environ", {"TERMINAN_GRID_DSN": "dummy"}, clear=True)
    def test_configured_not_probed(self):
        health = source_health()
        self.assertEqual(health["sources"]["cluster_grid"]["state"], "CONFIGURED_NOT_PROBED")
        self.assertNotIn("dummy", repr(health))
        self.assertEqual(health["sources"]["strattester_research"]["authority"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()

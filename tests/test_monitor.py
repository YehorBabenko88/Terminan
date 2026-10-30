import math
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from terminan.monitor import fleet_snapshot

NOW = datetime.now(timezone.utc)


class FleetTelemetryTests(unittest.TestCase):
    def snapshot(self, last_seen=NOW, cpu=20, ram=30, disk=100, symbols=2):
        with patch("terminan.monitor.grid_query", return_value=[
            ("node-1", "test-host", last_seen, cpu, ram, disk, symbols)
        ]):
            return fleet_snapshot()

    def test_recent_node(self):
        result = self.snapshot()
        self.assertEqual(result["online"], 1)
        self.assertEqual(result["nodes"][0]["cpu_pct"], 20)

    def test_future_timestamp_is_not_online(self):
        result = self.snapshot(last_seen=NOW + timedelta(days=1))
        self.assertEqual(result["online"], 0)
        self.assertIsNone(result["nodes"][0]["age_seconds"])

    def test_nonfinite_telemetry_rejected(self):
        for bad in (float("nan"), float("inf"), -1, 101):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.snapshot(cpu=bad)

    def test_invalid_disk_and_symbol_count(self):
        with self.assertRaises(ValueError):
            self.snapshot(disk=-1)
        with self.assertRaises(ValueError):
            self.snapshot(symbols=-1)

    def test_no_nodes(self):
        with patch("terminan.monitor.grid_query", return_value=[]):
            self.assertEqual(fleet_snapshot()["total"], 0)


if __name__ == "__main__":
    unittest.main()

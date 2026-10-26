"""Offline fail-closed integration provenance gates; no database or network access."""
import math
import unittest

PINNED_MAIN = {
    "Terminan": "fee79f4b15fc1f9efcff9ca12c403688b0026260",
    "strattester": "37ff7e9d12a4d2dccd788fc493c28557dbe8bcea",
    "bybit-cluster-grid": "d537d525296ef34f727996e240ae6c60102c6082",
}
MAX_MS = (1 << 63) - 1


def require_record(row, *, symbol, market_type, now_ms, max_age_ms):
    """Reject unverifiable historical availability, mixed symbols and stale data."""
    if not isinstance(row, dict) or row.get("schema_version") != 1:
        raise ValueError("unsupported schema")
    if row.get("symbol") != symbol or row.get("market_type") != market_type:
        raise ValueError("source identity mismatch")
    for key in ("event_ms", "source_ms", "available_ms"):
        v = row.get(key)
        if type(v) is not int or not 0 <= v <= MAX_MS:
            raise ValueError("invalid UTC milliseconds")
    if type(now_ms) is not int or type(max_age_ms) is not int or max_age_ms < 0:
        raise ValueError("invalid clock")
    if not row.get("source_id") or not row.get("snapshot_epoch"):
        raise ValueError("missing provenance")
    if row["event_ms"] > row["source_ms"] or row["source_ms"] > row["available_ms"]:
        raise ValueError("temporal inversion")
    if row["available_ms"] > now_ms:
        raise ValueError("future leakage")
    if now_ms - row["available_ms"] > max_age_ms:
        raise ValueError("stale source")
    if row.get("complete") is not True or row.get("coverage") != "COMPLETE":
        raise ValueError("partial coverage")
    for key in ("price", "volume"):
        value = row.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError("invalid numeric value")
    if row.get("kind") == "footprint" and row.get("authority") in ("LIVE_L2", "TRADING"):
        raise ValueError("footprint authority escalation")
    if row.get("kind") == "research":
        if not row.get("run_id") or row.get("authority") != "RESEARCH_ONLY":
            raise ValueError("research authority escalation")
    return True


class OfflineContracts(unittest.TestCase):
    def setUp(self):
        self.row = dict(schema_version=1, symbol="BTCUSDT", market_type="linear",
                        event_ms=1000, source_ms=1001, available_ms=1002,
                        source_id="fixture", snapshot_epoch="fixture-epoch",
                        complete=True, coverage="COMPLETE", price=1.0, volume=2.0,
                        kind="footprint", authority="HISTORICAL")

    def check(self, row):
        return require_record(row, symbol="BTCUSDT", market_type="linear",
                              now_ms=1003, max_age_ms=100)

    def test_valid_synthetic(self):
        self.assertTrue(self.check(self.row))

    def test_negative_mutations(self):
        mutations = [
            ("symbol", "ETHUSDT"), ("market_type", "spot"), ("schema_version", 2),
            ("event_ms", True), ("event_ms", 1.5), ("source_ms", -1),
            ("available_ms", 1004), ("available_ms", 500),
            ("source_id", ""), ("snapshot_epoch", ""),
            ("complete", False), ("coverage", "PARTIAL"),
            ("price", float("nan")), ("price", float("inf")),
            ("volume", None), ("volume", -1),
            ("authority", "LIVE_L2"), ("authority", "TRADING"),
        ]
        for field, value in mutations:
            with self.subTest(field=field, value=str(value)):
                with self.assertRaises(ValueError):
                    self.check(dict(self.row, **{field: value}))

    def test_temporal_inversion(self):
        with self.assertRaises(ValueError):
            self.check(dict(self.row, source_ms=999))

    def test_research_requires_run_and_research_only(self):
        with self.assertRaises(ValueError):
            self.check(dict(self.row, kind="research", run_id="", authority="RESEARCH_ONLY"))
        with self.assertRaises(ValueError):
            self.check(dict(self.row, kind="research", run_id="r1", authority="TRADING"))


if __name__ == "__main__":
    unittest.main()

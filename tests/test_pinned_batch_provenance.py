"""Additional fail-closed offline batch gates for cross-repository snapshots.

Synthetic fixtures only. This module never connects to a real source.
"""
import unittest


def validate_batch(records, *, expected_source, expected_epoch, expected_kind):
    if not isinstance(records, list) or not records:
        raise ValueError("source unavailable or empty batch")
    if not all(isinstance(v, str) and v for v in
               (expected_source, expected_epoch, expected_kind)):
        raise ValueError("missing expected provenance")
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("malformed source record")
        if record.get("source_id") != expected_source:
            raise ValueError("mixed source")
        if record.get("snapshot_epoch") != expected_epoch:
            raise ValueError("mixed snapshot epoch")
        if record.get("kind") != expected_kind:
            raise ValueError("mixed source type")
        if record.get("status") != "AVAILABLE":
            raise ValueError("stale or unavailable source")
        if record.get("complete") is not True:
            raise ValueError("partial source")
        if expected_kind == "research":
            identity = (record.get("run_id"), record.get("result_id"))
            if not all(isinstance(v, str) and v for v in identity):
                raise ValueError("missing research identity")
            if record.get("authority") != "RESEARCH_ONLY":
                raise ValueError("research authority escalation")
        else:
            identity = (record.get("symbol"), record.get("market_type"),
                        record.get("event_ms"), record.get("row_id"))
            if not all(v is not None and type(v) is not bool for v in identity):
                raise ValueError("missing market identity")
        if identity in seen:
            raise ValueError("duplicate source record")
        seen.add(identity)
    return True


class BatchContracts(unittest.TestCase):
    def setUp(self):
        self.record = dict(source_id="fixture-grid", snapshot_epoch="epoch-1",
                           kind="footprint", status="AVAILABLE", complete=True,
                           symbol="BTCUSDT", market_type="linear",
                           event_ms=1000, row_id="r1")
    def check(self, records):
        return validate_batch(records, expected_source="fixture-grid",
                              expected_epoch="epoch-1", expected_kind="footprint")
    def test_synthetic_valid(self):
        self.assertTrue(self.check([self.record]))
    def test_empty_unavailable(self):
        with self.assertRaises(ValueError):
            self.check([])
    def test_fail_closed_mutations(self):
        for field, value in [
            ("source_id", "other"), ("snapshot_epoch", "epoch-2"),
            ("kind", "research"), ("status", "STALE"),
            ("status", "UNAVAILABLE"), ("complete", False),
            ("row_id", None), ("market_type", None),
        ]:
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self.check([dict(self.record, **{field: value})])
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            self.check([self.record, dict(self.record)])
    def test_research_identity_and_authority(self):
        base = dict(self.record, kind="research", run_id="run1",
                    result_id="result1", authority="RESEARCH_ONLY")
        self.assertTrue(validate_batch([base], expected_source="fixture-grid",
                                       expected_epoch="epoch-1", expected_kind="research"))
        for patch in (dict(run_id=""), dict(result_id=None), dict(authority="TRADING")):
            with self.subTest(patch=patch):
                with self.assertRaises(ValueError):
                    validate_batch([dict(base, **patch)], expected_source="fixture-grid",
                                   expected_epoch="epoch-1", expected_kind="research")


if __name__ == "__main__":
    unittest.main()

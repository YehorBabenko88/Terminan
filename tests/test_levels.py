from contextlib import closing
from hashlib import sha256
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from threading import Thread
import unittest
from unittest.mock import patch

from terminan.levels import grid_level_candles, levels_from_grid_series, untouched_levels, merge_levels
from terminan.paper_ledger import canonical_json
from terminan.server import Handler

class LevelTests(unittest.TestCase):
    def test_high_low_touch_invalidation(self):
        h=3600000
        rows=[dict(t=0,h=100,l=90),dict(t=h,h=99,l=91),dict(t=2*h,h=101,l=92)]
        v=untouched_levels(rows,'1h',3*h)
        self.assertFalse(any(x['origin_ms']==0 and x['side']=='high' for x in v))
        self.assertTrue(any(x['origin_ms']==0 and x['side']=='low' for x in v))
    def test_no_future_candles(self):
        h=3600000
        self.assertEqual(untouched_levels([dict(t=0,h=5,l=1)],'1h',h-1),[])
    def test_incomplete_ignored(self):
        h=3600000
        self.assertEqual(untouched_levels([dict(t=0,h=5,l=1,complete=False)],'1h',h),[])
    def test_merge(self):
        h=3600000
        self.assertEqual(len(merge_levels({'1h':[dict(t=0,h=2,l=1)]},h)),2)
    def test_invalid(self):
        with self.assertRaises(ValueError): untouched_levels([], '1m', 0)

    def test_http_levels_does_not_read_unqualified_legacy_candles(self):
        with patch("terminan.server.data.candles") as legacy, \
                patch.object(Handler, "log_message"), \
                ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            worker = Thread(target=server.serve_forever)
            worker.start()
            try:
                with closing(HTTPConnection("127.0.0.1", server.server_port, timeout=5)) as client:
                    client.request("GET", "/api/levels?symbol=BTCUSDT")
                    with client.getresponse() as response:
                        self.assertEqual(response.status, 503)
                        self.assertEqual(json.load(response), {"error": "source unavailable"})
            finally:
                server.shutdown()
                worker.join()
        legacy.assert_not_called()

    def test_pinned_grid_rollup_projects_to_math_levels(self):
        hour = 3_600_000
        request = dict(venue="bybit", market_type="linear", symbol="BTCUSDT",
                       start_ms=0, end_ms=hour, as_of_ms=hour + 100)
        row = dict(event_start_ms=0, event_end_ms=hour, high=110.5, low=95.25,
                   available_at_ms=hour + 10, watermark_ms=hour)

        def signable(candle):
            payload = dict(schema="grid.history.rollup.v1", evidence_class="HISTORICAL",
                           request=request, timeframe="1h", rows=[candle], source={},
                           parent_dataset_id="fixture", parent_dataset_fingerprint="b" * 64)
            return dict(payload, dataset_fingerprint=sha256(canonical_json(payload)).hexdigest())

        def project(snapshot, pin=None, timeframe="1h"):
            return grid_level_candles(
                snapshot, trusted_fingerprint=pin or snapshot["dataset_fingerprint"],
                symbol="BTCUSDT", market_type="linear", timeframe=timeframe,
                start_ms=0, end_ms=hour, as_of_ms=hour + 100)

        original = signable(row)
        candles = project(original)
        self.assertEqual(candles, [dict(t=0, h=110.5, l=95.25, complete=True)])
        self.assertEqual([value["price"] for value in untouched_levels(candles, "1h", hour)],
                         [110.5, 95.25])
        for invalid in (dict(row, complete=False), dict(row, event_end_ms=hour - 1),
                        dict(row, event_start_ms=60_000), dict(row, high=-1),
                        dict(row, available_at_ms=hour + 101)):
            with self.subTest(row=invalid), self.assertRaises(ValueError):
                project(signable(invalid))
        with self.assertRaises(ValueError):
            project(original, "a" * 64)
        with self.assertRaises(ValueError):
            project(dict(original, rows=[dict(row, high=500)]))
        with self.assertRaises(ValueError):
            project(original, timeframe="4h")

    def test_multipin_projects_all_math_timeframes_and_checks_parent_order(self):
        day = 86_400_000
        for timeframe, start, width in (
            ("1h", 0, 3_600_000), ("4h", 0, 14_400_000),
            ("1d", 0, day), ("1w", 4 * day, 7 * day),
        ):
            with self.subTest(timeframe=timeframe):
                end = start + width
                request = dict(venue="bybit", market_type="linear", symbol="BTCUSDT",
                               start_ms=start, end_ms=end, timeframe=timeframe,
                               snapshot_ids=["a" * 64, "b" * 64])
                parents = [dict(snapshot_id=pin, dataset_id=str(i), dataset_fingerprint="c" * 64)
                           for i, pin in enumerate(request["snapshot_ids"])]
                row = dict(event_start_ms=start, event_end_ms=end, high=10, low=5,
                           watermark_ms=end, available_at_ms=end)
                payload = dict(schema="grid.history.rollup.v2", timeframe=timeframe, source={},
                               evidence_class="HISTORICAL", request=request, units={},
                               as_of_ms=end, parents=parents, rows=[row])

                def project(snapshot):
                    pin = sha256(canonical_json(snapshot)).hexdigest()
                    return grid_level_candles(
                        dict(snapshot, dataset_fingerprint=pin), trusted_fingerprint=pin,
                        symbol="BTCUSDT", market_type="linear", timeframe=timeframe,
                        start_ms=start, end_ms=end, as_of_ms=end)

                self.assertEqual(project(payload), [dict(t=start, h=10, l=5, complete=True)])
                with self.assertRaises(ValueError):
                    project(dict(payload, parents=list(reversed(parents))))

    def test_series_checks_continuity_and_lineage_before_calculating_levels(self):
        width = 3_600_000
        end = 2 * width

        def candle(start, high, low):
            stop = start + width
            return dict(event_start_ms=start, event_end_ms=stop, high=high, low=low,
                        watermark_ms=stop, available_at_ms=stop)

        first, second = candle(0, 20, 5), candle(width, 15, 7)
        parent = dict(snapshot_id="a" * 64, dataset_id="page", dataset_fingerprint="b" * 64)
        payload = dict(schema="grid.history.rollup.v3", timeframe="1h",
                       source=dict(identity="grid-bybit", source_revision="one", epoch="one"),
                       evidence_class="HISTORICAL", as_of_ms=end,
                       units=dict(price="quote/base", volume="base"), parents=[parent],
                       request=dict(schema="grid.history.selection.v4", venue="bybit",
                                    market_type="linear", symbol="BTCUSDT", start_ms=0,
                                    end_ms=end, timeframe="1h", snapshot_ids=[parent["snapshot_id"]]),
                       rows=[first, second])

        def levels(response, pin=None):
            fingerprint = sha256(canonical_json(response)).hexdigest()
            return levels_from_grid_series(
                dict(response, dataset_fingerprint=fingerprint),
                trusted_fingerprint=pin or fingerprint, symbol="BTCUSDT",
                market_type="linear", timeframe="1h", start_ms=0, end_ms=end, as_of_ms=end,
            )

        combined = levels(payload)
        self.assertEqual({item["price"] for item in combined}, {20, 5, 15, 7})
        with patch("terminan.levels.untouched_levels") as compute:
            for response, pin in [
                (dict(payload, rows=[first]), None), (dict(payload, rows=[second, first]), None),
                (dict(payload, rows=[first, first]), None), (payload, "d" * 64),
                (dict(payload, rows=[first, candle(end, 15, 7)]), None),
                (dict(payload, source=dict(identity="grid-bybit", source_revision="one")), None),
                (dict(payload, rows=[first, dict(second, available_at_ms=end + 1)]), None),
            ]:
                with self.subTest(response=response), self.assertRaises(ValueError):
                    levels(response, pin)
            compute.assert_not_called()

    def test_grid_timestamp_cannot_exceed_producer_safe_integer_range(self):
        hour = 3_600_000
        snapshot = dict(
            schema="grid.history.rollup.v1", timeframe="1h", evidence_class="HISTORICAL",
            source={}, parent_dataset_id="legacy", parent_dataset_fingerprint="b" * 64,
            request=dict(venue="bybit", symbol="BTCUSDT", market_type="linear",
                         start_ms=0, end_ms=hour, as_of_ms=2**53),
            rows=[dict(event_start_ms=0, event_end_ms=hour, available_at_ms=hour,
                       watermark_ms=hour, high=10, low=5)],
        )
        pin = sha256(canonical_json(snapshot)).hexdigest()
        with self.assertRaisesRegex(ValueError, "window"):
            grid_level_candles(
                dict(snapshot, dataset_fingerprint=pin), trusted_fingerprint=pin,
                symbol="BTCUSDT", market_type="linear", timeframe="1h",
                start_ms=0, end_ms=hour, as_of_ms=2**53,
            )

if __name__=='__main__':unittest.main()

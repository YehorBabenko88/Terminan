"""Pinned B market_data_v2 managed HTTP -> D Terminan consumer, inert.

Sources are supplied by the dedicated D/B GitHub Actions matrix. This suite
uses canonical synthetic minute_record bytes and a reader-only in-memory seam.
It does NOT demonstrate PostgreSQL custody, source authenticity, or permission
to execute paper/real orders.
"""
import copy
import json
import os
import sys
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

for key in ("ROUND3_MATH_SOURCE", "ROUND3_GRID_SOURCE"):
    source = os.environ.get(key)
    if not source or not os.path.isabs(source):
        raise RuntimeError("PINNED_ROUND3_SOURCE_REQUIRED")
    sys.path.insert(0, source)

from market_data.provenance import minute_record, producer
from market_data import history_api
from market_data_v2 import read_api
from terminan import data
from terminan.qualified_partial import _V2_KEYS


def record_fixture(now_ms):
    start = (now_ms // 60000 - 1) * 60000
    source = producer("synthetic-lab-source", "a" * 40,
                      "wss://stream.bybit.com/v5/public/linear")
    row = dict(symbol="BTCUSDT", start_ms=start,
               source_event_start_ms=start + 1,
               source_event_end_ms=start + 59999,
               source_provenance=source,
               open=2, high=2, low=2, close=2,
               buy_volume=1, sell_volume=0, delta=1,
               trade_count=1, poc_price=2, quality_status="GOOD",
               quality_reasons=[],
               levels=[dict(price=2, buy_volume=1, sell_volume=0,
                            delta=1, volume=1, buy_count=1, sell_count=0)])
    record = minute_record(row, now_ms, "synthetic-lab-source")
    assert record["status"] == "PARTIAL"
    return record


class Admission:
    def __init__(self):
        self.current = True
    def require_current(self):
        if not self.current:
            raise ValueError("SOURCE_REVOKED")
        return True
    def source_identity(self, module_id):
        if module_id != "market_data":
            raise ValueError("WRONG_SOURCE")
        return {"commit": "a" * 40}


class Bv2ToTerminanReadTests(unittest.TestCase):
    def setUp(self):
        self.admission = Admission()
        self.token = "b" * 64
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), read_api.Handler)
        self.server.daemon_threads = True
        self.server.module_identity = {"instance_token": self.token}
        self.server.startup_admission = self.admission
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()
        self.old = data._private_market_data_client
        self.cap = dict(port=self.server.server_port, token=self.token,
                        source_commit="a" * 40, release_id="d-round3",
                        epoch="c" * 32)
        data._private_market_data_client = data.MarketDataReadClient(
            self.cap, self.admission, "d-round3")
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        data._private_market_data_client = self.old
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def test_b_published_json_schema_keys_match_closed_d_consumer(self):
        path = os.path.join(os.environ["ROUND3_GRID_SOURCE"],
                            "docs", "contracts",
                            "qualified-read-envelope-v1.schema.json")
        with open(path, encoding="utf-8") as source:
            schema = json.load(source)
        self.assertEqual(schema["additionalProperties"], False)
        self.assertEqual(set(schema["properties"]), _V2_KEYS)
        self.assertEqual(read_api.ROUTE, "/internal/v2/candles/qualified")

    def test_real_v2_handler_uses_same_managed_listener_and_math_rows(self):
        rows = [record_fixture(int(time.time() * 1000))]
        with patch.object(history_api, "immutable_minutes",
                          side_effect=lambda symbol, limit, before: rows):
            receipt = data.qualified_market_data_chart("BTCUSDT", 1)
        self.assertEqual(receipt["status"], "PARTIAL")
        self.assertEqual(receipt["record_integrity"], "VERIFIED")
        self.assertEqual(receipt["source_authenticity"], "NOT_INDEPENDENTLY_ATTESTED")
        self.assertEqual(receipt["quality_attestation"], "NOT_INDEPENDENTLY_ATTESTED")
        self.assertEqual(receipt["storage_immutability"], "NOT_ATTESTED")
        self.assertEqual(len(receipt["rows"]), 1)
        self.assertEqual(receipt["rows"][0]["poc"], 2)
        self.assertFalse(receipt["exchange_completeness_attested"])
        self.assertFalse(receipt["paper_admitted"])
        self.assertFalse(receipt["trading_authorized"])
        self.assertFalse(receipt["execution_authority"])

    def test_tamper_and_legacy_unavailable_are_never_displayed(self):
        row = record_fixture(int(time.time() * 1000))
        altered = copy.deepcopy(row)
        altered["candle"]["high"] = 0
        for payload in ([altered], [dict(row, producer="bybit-cluster-grid")], []):
            with self.subTest(record_count=len(payload)):
                with patch.object(history_api, "immutable_minutes",
                                  side_effect=lambda symbol, limit, before: payload):
                    value = data.qualified_market_data_chart("BTCUSDT", 1)
                self.assertEqual(value["status"], "UNAVAILABLE")
                self.assertFalse(value["paper_admitted"])
                self.assertEqual(value["rows"], [])

    def test_wrong_token_and_post_read_revocation_never_release_chart(self):
        row = record_fixture(int(time.time() * 1000))
        bad = {**self.cap, "token": "d" * 64}
        data._private_market_data_client = data.MarketDataReadClient(
            bad, self.admission, "d-round3")
        with patch.object(history_api, "immutable_minutes",
                          side_effect=lambda symbol, limit, before: [row]):
            denied = data.qualified_market_data_chart("BTCUSDT", 1)
        self.assertEqual(denied["status"], "UNAVAILABLE")
        self.assertFalse(denied["paper_admitted"])

        data._private_market_data_client = data.MarketDataReadClient(
            self.cap, self.admission, "d-round3")
        def revoke_after_read(*_):
            self.admission.current = False
            return [row]
        with patch.object(history_api, "immutable_minutes",
                          side_effect=revoke_after_read):
            refused = data.qualified_market_data_chart("BTCUSDT", 1)
        self.assertEqual(refused["status"], "UNAVAILABLE")
        self.assertEqual(refused["rows"], [])
        self.assertFalse(refused["execution_authority"])


    def test_b_exact_status_matrix_has_no_d_authority_promotion(self):
        """Exercise actual pinned B qualifier, real managed HTTP and D consumer.

        B owns GAP/STALE/UNAVAILABLE status labels, while D intentionally
        returns only a fail-closed UNAVAILABLE chart for each non-PARTIAL
        state. This does not require a PostgreSQL or network feed.
        """
        minute = 60000
        now = int(time.time() * 1000)
        first = record_fixture(now)
        # A late event from an earlier minute is still source-continuous
        # only with the immediately following minute present.
        def shift(row, offset):
            item = copy.deepcopy(row)
            for key in ("start_ms", "end_ms", "source_event_start_ms",
                        "source_event_end_ms", "ingestion_ms"):
                item[key] += offset
            from market_data.provenance import digest
            item["dataset_fingerprint"] = digest({
                k: v for k, v in item.items() if k != "dataset_fingerprint"
            })
            return item

        cases = [
            ("PARTIAL", [first], "PARTIAL"),
            ("GAP", [shift(first, -2 * minute), first], "UNAVAILABLE"),
            ("STALE", [shift(first, -5 * minute)], "UNAVAILABLE"),
            ("UNAVAILABLE", [], "UNAVAILABLE"),
        ]
        for origin, rows, d_status in cases:
            with self.subTest(origin=origin):
                with patch.object(history_api, "immutable_minutes",
                                  return_value=rows):
                    # Capture the actual B DTO on the same managed HTTP
                    # endpoint; no hand-authored status replacement.
                    raw = data._private_market_data_client.get(
                        "/internal/v2/candles/qualified?symbol=BTCUSDT&limit=2")
                    self.assertEqual(raw["status"], origin)
                    self.assertFalse(raw["execution_authority"])
                    self.assertFalse(raw["paper_admitted"])
                    self.assertFalse(raw["trading_authorized"])
                    receipt = data.qualified_market_data_chart("BTCUSDT", 2)
                self.assertEqual(receipt["status"], d_status)
                self.assertFalse(receipt["paper_admitted"])
                self.assertFalse(receipt["execution_authority"])
                self.assertFalse(receipt["trading_authorized"])
                if origin != "PARTIAL":
                    self.assertEqual(receipt["rows"], [])
                else:
                    self.assertEqual(len(receipt["rows"]), 1)
                    self.assertEqual(receipt["record_integrity"], "VERIFIED")

    def test_b_qualified_page_rejects_cross_epoch_not_retrospective_cure(self):
        """A correctly rehashed mixed-epoch page remains a GAP, not chart."""
        from market_data.provenance import digest
        now = int(time.time() * 1000)
        newest = record_fixture(now)
        older = copy.deepcopy(newest)
        for field in ("start_ms", "end_ms", "source_event_start_ms",
                      "source_event_end_ms", "ingestion_ms"):
            older[field] -= 60000
        older["source"]["epoch"] = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
        older["dataset_fingerprint"] = digest({
            k: v for k, v in older.items() if k != "dataset_fingerprint"
        })
        with patch.object(history_api, "immutable_minutes",
                          return_value=[newest, older]):
            raw = data._private_market_data_client.get(
                "/internal/v2/candles/qualified?symbol=BTCUSDT&limit=2")
            self.assertEqual(raw["status"], "GAP")
            self.assertEqual(raw["reason"], "MISSING_MINUTES_OR_EPOCH_CHANGE")
            self.assertFalse(raw["paper_admitted"])
            receipt = data.qualified_market_data_chart("BTCUSDT", 2)
        self.assertEqual(receipt["status"], "UNAVAILABLE")
        self.assertEqual(receipt["rows"], [])
        self.assertFalse(receipt["paper_admitted"])
        self.assertFalse(receipt["trading_authorized"])


    @staticmethod
    def _mtf_records(boundary_ms, ingestion_ms, count):
        """One source epoch, real minute_record producer and closed 1m cells."""
        source = producer("synthetic-lab-source", "a" * 40,
                          "wss://stream.bybit.com/v5/public/linear")
        records = []
        for index in range(count):
            start = boundary_ms - (count - index) * 60000
            row = dict(symbol="BTCUSDT", start_ms=start,
                       source_event_start_ms=start + 1,
                       source_event_end_ms=start + 59999,
                       source_provenance=source,
                       open=2, high=2, low=2, close=2,
                       buy_volume=1, sell_volume=0, delta=1,
                       trade_count=1, poc_price=2,
                       quality_status="GOOD", quality_reasons=[],
                       levels=[dict(price=2, buy_volume=1,
                                    sell_volume=0, delta=1, volume=1,
                                    buy_count=1, sell_count=0)])
            record = minute_record(row, ingestion_ms, "synthetic-lab-source")
            if record["status"] != "PARTIAL":
                raise AssertionError("INVALID_CANONICAL_MINUTE_FIXTURE")
            records.append(record)
        return records

    def test_b_managed_75_minutes_to_math_5m_15m_readonly(self):
        """Actual managed B rollup route, strict D projection, Math checks."""
        from decimal import Decimal
        boundary = ((int(time.time() * 1000) // 900000) + 1) * 900000
        now = boundary + 30000
        rows = self._mtf_records(boundary, now, 75)
        with (
            patch.object(history_api, "immutable_minutes",
                         side_effect=lambda symbol, limit, before: rows[-limit:]) as reader,
            patch("market_data_v2.read_api.time.time", return_value=now / 1000),
        ):
            fifteen = data.qualified_market_data_timeframe_chart(
                "BTCUSDT", "15m", bars=5)
            five = data.qualified_market_data_timeframe_chart(
                "BTCUSDT", "5m", bars=5)
        reader.assert_any_call("BTCUSDT", 75, boundary)
        reader.assert_any_call("BTCUSDT", 25, boundary)
        for result, volume, timeframe in (
                (fifteen, "15", "15m"), (five, "5", "5m")):
            with self.subTest(timeframe=timeframe):
                self.assertEqual(result["status"], "PARTIAL")
                self.assertEqual(result["timeframe"], timeframe)
                self.assertEqual(len(result["rows"]), 5)
                self.assertEqual(Decimal(result["rows"][0]["v"]), Decimal(volume))
                self.assertRegex(result["dataset_fingerprint"], r"^[a-f0-9]{64}$")
                self.assertRegex(result["parent_dataset_fingerprint"], r"^[a-f0-9]{64}$")
                self.assertEqual(result["source_revision_declared"], "a" * 40)
                self.assertFalse(result["paper_admitted"])
                self.assertFalse(result["trading_authorized"])
                self.assertFalse(result["execution_authority"])
                self.assertFalse(result["exchange_completeness_attested"])
                self.assertEqual(result["rows"][-1]["closed_at_ms"], boundary)

    def test_b_mtf_gaps_epoch_stale_and_unaligned_are_refused(self):
        from market_data.provenance import digest
        boundary = ((int(time.time() * 1000) // 900000) + 1) * 900000
        now = boundary + 30000
        rows = self._mtf_records(boundary, now, 75)
        cross_epoch = copy.deepcopy(rows)
        cross_epoch[20]["source"]["epoch"] = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
        cross_epoch[20]["dataset_fingerprint"] = digest({
            key: value for key, value in cross_epoch[20].items()
            if key != "dataset_fingerprint"
        })
        cases = (
            ("GAP", rows[:35] + rows[36:], now),
            ("MIXED_EPOCH", cross_epoch, now),
            ("INCOMPLETE_60", rows[-60:], now),
            ("STALE", rows, boundary + 180001),
            ("UNALIGNED", self._mtf_records(boundary - 60000, now, 75), now),
            ("EMPTY", [], now),
        )
        for reason, records, clock in cases:
            with (
                self.subTest(reason=reason),
                patch.object(history_api, "immutable_minutes",
                             return_value=records),
                patch("market_data_v2.read_api.time.time",
                      return_value=clock / 1000),
            ):
                receipt = data.qualified_market_data_timeframe_chart(
                    "BTCUSDT", "15m", bars=5)
                self.assertEqual(receipt["status"], "UNAVAILABLE")
                self.assertEqual(receipt["rows"], [])
                self.assertFalse(receipt["paper_admitted"])
                self.assertFalse(receipt["execution_authority"])
                self.assertFalse(receipt["trading_authorized"])

    def test_grid_mtf_digest_and_math_negative_matrix(self):
        """Rehashing a forged B page never converts it to a qualified chart."""
        from market_data.provenance import digest
        from market_data_v2.read_api import qualified_rollup_snapshot
        from terminan.qualified_rollup import validate_qualified_rollup
        boundary = ((int(time.time() * 1000) // 900000) + 1) * 900000
        now = boundary + 30000
        rows = self._mtf_records(boundary, now, 5)
        page = qualified_rollup_snapshot(
            "BTCUSDT", "5m", 1, reader=lambda *_: rows, now_ms=now,
            exact=True)
        self.assertEqual(
            validate_qualified_rollup(page, "BTCUSDT", "5m", 1,
                                      now_ms=now, exact=True)["status"], "PARTIAL")
        changes = (
            lambda p: p.update(status="STALE"),
            lambda p: p.update(paper_admitted=True),
            lambda p: p.update(execution_authority=True),
            lambda p: p.update(source_authenticity="EXCHANGE_VERIFIED"),
            lambda p: p.update(source_minutes=True),
            lambda p: p["rows"][0].update(delta=1.2345),
            lambda p: p["rows"][0].update(high=0),
            lambda p: p["rows"][0].update(trade_count=True),
            lambda p: p["rows"][0].update(end_ms=p["rows"][0]["end_ms"] - 1),
            lambda p: p["rows"][0].update(source_minute_fingerprints=[]),
            lambda p: p["rows"][0]["source_minute_fingerprints"].__setitem__(
                1, p["rows"][0]["source_minute_fingerprints"][0]),
            lambda p: p["rows"][0].update(buy_volume=-1),
            lambda p: p["coverage"].update(missing_minutes=True),
            lambda p: p.update(debug="injected"),
        )
        for mutate in changes:
            forged = copy.deepcopy(page)
            mutate(forged)
            forged["dataset_fingerprint"] = digest({
                key: value for key, value in forged.items()
                if key != "dataset_fingerprint"
            })
            with self.subTest(mutate=str(mutate)), self.assertRaises(ValueError):
                validate_qualified_rollup(
                    forged, "BTCUSDT", "5m", 1, now_ms=now, exact=True)


    def test_b305_history_separate_from_live_and_stale(self):
        """Managed B305 historical as-of works only as source-only observation."""
        boundary = ((int(time.time() * 1000) // 900000) - 4) * 900000
        asof = boundary + 60000
        rows = self._mtf_records(boundary, boundary + 30000, 15)
        with patch.object(history_api, "immutable_minutes",
                          return_value=rows) as reader:
            hist = data.qualified_market_data_historical_chart(
                "BTCUSDT", "5m", bars=3,
                before_ms=boundary, as_of_ms=asof)
            live = data.qualified_market_data_timeframe_chart(
                "BTCUSDT", "5m", bars=3)
        self.assertEqual(hist["status"], "PARTIAL")
        self.assertEqual(hist["reason"], "HISTORICAL_AS_OF_SOURCE_ONLY")
        self.assertEqual(hist["observation_mode"], "HISTORICAL_AS_OF_SOURCE_ONLY")
        self.assertEqual(hist["historical_source_trust"],
                         "NOT_INDEPENDENTLY_ATTESTED")
        self.assertEqual(hist["live_freshness"], "NOT_APPLICABLE")
        self.assertEqual(hist["as_of_ms"], asof)
        self.assertEqual(hist["before_ms"], boundary)
        self.assertEqual(len(hist["rows"]), 3)
        self.assertFalse(hist["paper_admitted"])
        self.assertFalse(hist["trading_authorized"])
        self.assertFalse(hist["execution_authority"])
        self.assertFalse(hist["exchange_completeness_attested"])
        self.assertEqual(live["status"], "UNAVAILABLE")
        self.assertEqual(live["rows"], [])
        reader.assert_any_call("BTCUSDT", 15, boundary)

    def test_b305_historical_source_lookahead_gap_and_epoch_refused(self):
        from market_data.provenance import digest
        boundary = ((int(time.time() * 1000) // 900000) - 4) * 900000
        asof = boundary + 60000
        base = self._mtf_records(boundary, boundary + 30000, 15)
        too_late = self._mtf_records(boundary, asof + 60000, 15)
        mixed = copy.deepcopy(base)
        mixed[7]["source"]["epoch"] = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
        mixed[7]["dataset_fingerprint"] = digest({
            key:value for key,value in mixed[7].items()
            if key != "dataset_fingerprint"})
        for reason, records in (
            ("INGEST_AFTER_ASOF", too_late),
            ("MISSING_MINUTE", base[:8] + base[9:]),
            ("MIXED_SOURCE_EPOCH", mixed),
            ("NO_SOURCE", []),
        ):
            with self.subTest(reason=reason), patch.object(
                history_api, "immutable_minutes", return_value=records
            ):
                hist = data.qualified_market_data_historical_chart(
                    "BTCUSDT", "5m", bars=3,
                    before_ms=boundary, as_of_ms=asof)
                self.assertEqual(hist["status"], "UNAVAILABLE")
                self.assertEqual(hist["rows"], [])
                self.assertFalse(hist["paper_admitted"])
                self.assertFalse(hist["trading_authorized"])
                self.assertFalse(hist["execution_authority"])

    def test_b305_decimal_cancellation_remains_visible_in_d_chart(self):
        """Grid's source Math delta=0.01 survives lossy binary64 volumes."""
        from market_data.provenance import digest
        boundary = ((int(time.time() * 1000) // 900000) - 4) * 900000
        asof = boundary + 60000
        rows = self._mtf_records(boundary, boundary + 30000, 5)
        for i, item in enumerate(rows):
            buy = 1e16 if i == 0 else (1.01 if i == 1 else 1.0)
            sell = 1e16 if i == 0 else 1.0
            delta = 0.01 if i == 1 else 0.0
            item["candle"].update(buy_volume=buy, sell_volume=sell, delta=delta)
            item["levels"][0].update(
                buy_volume=buy, sell_volume=sell, delta=delta,
                volume=buy + sell)
            item["dataset_fingerprint"] = digest({
                k:v for k,v in item.items()
                if k != "dataset_fingerprint"})
        with patch.object(history_api, "immutable_minutes", return_value=rows):
            hist = data.qualified_market_data_historical_chart(
                "BTCUSDT", "5m", bars=1,
                before_ms=boundary, as_of_ms=asof)
        self.assertEqual(hist["status"], "PARTIAL")
        self.assertEqual(hist["rows"][0]["buy_volume"],
                         hist["rows"][0]["sell_volume"])
        self.assertEqual(hist["rows"][0]["delta"], 0.01)
        # Canonical Math restores precise aggregate over the stored source
        # minute JSON numbers. It does NOT claim original raw exchange ticks.
        from decimal import Decimal
        self.assertEqual(hist["rows"][0]["volume_precision"],
                         "EXACT_STORED_1M_JSON_NUMBERS_NOT_PROVIDER_RAW")
        self.assertEqual(hist["volume_precision"],
                         "EXACT_STORED_1M_JSON_NUMBERS_NOT_PROVIDER_RAW")
        self.assertEqual(Decimal(hist["rows"][0]["v"]),
                         Decimal("20000000000000008.01"))
        self.assertEqual(hist["rows"][0]["delta_decimal"], "0.01")
        self.assertEqual(hist["rows"][0]["volume_decimal"],
                         "20000000000000008.01")
        self.assertEqual(hist["source_numeric_precision"],
                         "STORED_1M_JSON_NUMBERS_NOT_PROVIDER_RAW")
        self.assertFalse(hist["paper_admitted"])
        self.assertFalse(hist["trading_authorized"])

    def test_grid_exact_129_digit_valid_15m_math_sum_is_retained(self):
        """Single-minute 128-digit bounds must not cap 15-minute exact sums."""
        from decimal import Decimal
        from market_data.provenance import digest
        from market_data_v2.read_api import qualified_rollup_snapshot
        from terminan.qualified_rollup import (
            chart_rollup_rows, validate_qualified_rollup,
        )
        boundary = ((int(time.time() * 1000) // 900000) + 1) * 900000
        now = boundary + 30000
        records = self._mtf_records(boundary, now, 15)
        amount = 10 ** 127
        for item in records:
            item["candle"].update(
                buy_volume=amount, sell_volume=0,
                delta=amount)
            item["levels"][0].update(
                buy_volume=amount, sell_volume=0,
                volume=amount, delta=amount)
            item["dataset_fingerprint"] = digest({
                key:value for key,value in item.items()
                if key != "dataset_fingerprint"})
        page = qualified_rollup_snapshot(
            "BTCUSDT", "15m", 1,
            reader=lambda *_:records, now_ms=now, exact=True)
        checked = validate_qualified_rollup(
            page, "BTCUSDT", "15m", 1, now_ms=now, exact=True)
        display = chart_rollup_rows(checked)
        self.assertEqual(Decimal(display[0]["v"]), Decimal(15 * amount))
        self.assertEqual(display[0]["volume_decimal"],
                         str(15 * amount))
        self.assertEqual(display[0]["volume_precision"],
                         "EXACT_STORED_1M_JSON_NUMBERS_NOT_PROVIDER_RAW")
        self.assertFalse(checked["paper_admitted"])
        self.assertFalse(checked["trading_authorized"])

    def test_b305_historical_dto_tampering_rehashed_still_refused(self):
        """Integrity hash alone cannot raise source or execution authority."""
        from market_data.provenance import digest
        from market_data_v2.read_api import historical_asof_snapshot
        from terminan.qualified_rollup import validate_qualified_rollup
        boundary = ((int(time.time() * 1000) // 900000) - 4) * 900000
        asof = boundary + 60000
        rows = self._mtf_records(boundary, boundary + 30000, 5)
        page = historical_asof_snapshot(
            "BTCUSDT", "5m", 1, boundary, asof,
            reader=lambda *_:rows, now_ms=int(time.time()*1000),
            exact=True)
        self.assertEqual(validate_qualified_rollup(
            page, "BTCUSDT", "5m", 1, historical=True,
            before_ms=boundary, as_of_ms=asof,
            exact=True)["status"], "PARTIAL")
        changes = (
            lambda p: p.update(source_declared_quality=["DEGRADED"]),
            lambda p: p.update(decimal_contract="SOURCE_VERIFIED"),
            lambda p: p.update(source_numeric_precision="RAW_EXCHANGE_TICKS"),
            lambda p: p["rows"][0].update(volume_decimal="99999"),
            lambda p: p["rows"][0].update(delta_decimal="1E+3"),
            lambda p: p["rows"][0].update(buy_volume_decimal="-0"),
            lambda p: p["rows"][0].update(sell_volume_decimal="01"),
            lambda p: p["rows"][0].update(volume_decimal="1.00"),
            lambda p: p["rows"][0].update(delta_decimal="NaN"),
            lambda p: p["rows"][0].update(volume_decimal="9"*4301),
            lambda p: p.update(historical_source_trust="EXCHANGE_VERIFIED"),
            lambda p: p.update(live_freshness="FRESH"),
            lambda p: p.update(freshness_mode="LIVE"),
            lambda p: p.update(as_of_ms=asof + 60000),
            lambda p: p.update(paper_admitted=True),
            lambda p: p["rows"][0].update(delta=999999.0),
            lambda p: p.update(extra_authority="YES"),
        )
        for change in changes:
            forged = copy.deepcopy(page)
            change(forged)
            forged["dataset_fingerprint"] = digest({
                k:v for k,v in forged.items()
                if k != "dataset_fingerprint"})
            with self.subTest(change=str(change)), self.assertRaises(ValueError):
                validate_qualified_rollup(
                    forged, "BTCUSDT", "5m", 1,
                    historical=True, before_ms=boundary, as_of_ms=asof,
                    exact=True)

    def test_old_capability_cannot_read_after_grid_restart_or_get_v1_fallback(self):
        """Real loopback Grid Handler restart, not an in-memory HTTP mock.

        This deliberately does not simulate Consul/OS process quiescence; it
        proves D cannot use the old bearer and port as a v1 fallback after
        source loss, nor treat a replacement process as the same owner.
        """
        original_server = self.server
        original_thread = self.thread
        old_port = original_server.server_port
        old_capability = dict(self.cap)
        old_client = data._private_market_data_client
        original_server.shutdown()
        original_server.server_close()
        original_thread.join(timeout=3)
        self.assertFalse(original_thread.is_alive())

        # First control: stopped B listener must not yield cached PARTIAL.
        stopped = data.qualified_market_data_chart("BTCUSDT", 1)
        self.assertEqual(stopped["status"], "UNAVAILABLE")
        self.assertEqual(stopped["rows"], [])
        self.assertFalse(stopped["paper_admitted"])
        self.assertFalse(stopped["execution_authority"])

        from unittest.mock import patch as _patch
        # Rebind the SAME port: a stale D client can still reach a healthy
        # replacement listener, so port closure alone cannot establish epoch
        # revocation. The fresh Grid process-local bearer is the HTTP fence.
        replacement = ThreadingHTTPServer(("127.0.0.1", old_port),
                                           read_api.Handler)
        replacement.daemon_threads = True
        new_token = "e" * 64
        replacement.module_identity = {"instance_token": new_token}
        replacement.startup_admission = self.admission
        replacement_thread = threading.Thread(
            target=replacement.serve_forever, daemon=True)
        replacement_thread.start()
        try:
            # Even if old and new Grid code have the same Git source commit,
            # process-local tokens and lease epochs must NOT be reused.
            self.assertNotEqual(new_token, old_capability["token"])
            self.assertEqual(replacement.server_port, old_port)
            row = record_fixture(int(time.time() * 1000))
            with _patch.object(history_api, "immutable_minutes",
                               return_value=[row]) as sql_reader:
                # The ORIGINAL D client still points at the SAME live port
                # with a stale bearer/epoch. Grid must reject the request
                # BEFORE accessing the underlying canonical SQL reader.
                data._private_market_data_client = old_client
                refused = data.qualified_market_data_chart("BTCUSDT", 1)
                self.assertEqual(refused["status"], "UNAVAILABLE")
                self.assertFalse(refused["paper_admitted"])
                self.assertEqual(refused["rows"], [])
                self.assertFalse(refused["execution_authority"])
                sql_reader.assert_not_called()

                # A fresh test capability for the replacement listener is
                # distinct, chart-only, and never authorizes trading.
                new_capability = dict(old_capability,
                                      port=old_port,
                                      token=new_token, epoch="d" * 32)
                data._private_market_data_client = data.MarketDataReadClient(
                    new_capability, self.admission, "d-round3")
                fresh = data.qualified_market_data_chart("BTCUSDT", 1)
                self.assertEqual(fresh["status"], "PARTIAL")
                self.assertEqual(fresh["record_integrity"], "VERIFIED")
                self.assertFalse(fresh["paper_admitted"])
                self.assertFalse(fresh["trading_authorized"])
                self.assertFalse(fresh["execution_authority"])

            # A revoked source admission refuses even the new bearer/epoch.
            self.admission.current = False
            revoked = data.qualified_market_data_chart("BTCUSDT", 1)
            self.assertEqual(revoked["status"], "UNAVAILABLE")
            self.assertFalse(revoked["paper_admitted"])
            self.assertEqual(revoked["rows"], [])
        finally:
            data._private_market_data_client = old_client
            replacement.shutdown()
            replacement.server_close()
            replacement_thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()

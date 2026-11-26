"""Independent Grid→Terminan PARTIAL read-only fixture and refusal tests."""
import copy
import http.client
import json
import os
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from unittest import mock

from terminan import data
from terminan.qualified_partial import validate_partial, chart_rows, _digest
from market_data.provenance import minute_record, producer
from market_data.provenance_gateway import read_snapshot


def fixture(now, *, count=1):
    source = producer("fixture", "a" * 40,
                      "wss://stream.bybit.com/v5/public/linear")
    source_start = ((now // 60000) - 1) * 60000
    records = []
    for index in range(count):
        start = source_start - index * 60000
        row = {
            "symbol": "BTCUSDT", "start_ms": start,
            "source_event_start_ms": start + 1,
            "source_event_end_ms": start + 59999,
            "source_provenance": copy.deepcopy(source),
            "open": 2, "high": 2, "low": 2, "close": 2,
            "buy_volume": 1, "sell_volume": 0, "delta": 1,
            "trade_count": 1, "poc_price": 2,
            "quality_status": "GOOD", "quality_reasons": [],
            "levels": [{"price": 2, "buy_volume": 1, "sell_volume": 0,
                        "delta": 1, "volume": 1,
                        "buy_count": 1, "sell_count": 0}],
        }
        records.append(minute_record(row, now, "fixture"))
    initial = {
        "api_version": {"major": 1, "minor": 0}, "producer": "market_data",
        "read_only": True, "status": "UNAVAILABLE",
        "reason": "SOURCE_PROVENANCE_UNAVAILABLE",
        "symbol": "BTCUSDT", "limit": count, "timeframe": "1m",
        "rows": [], "representation": "historical_aggregate",
        "execution_authority": False,
    }
    with mock.patch.dict(os.environ, {"MARKET_DATA_PROVENANCE_READ": "1"}), (
        mock.patch("market_data.provenance_gateway.time.time", return_value=now / 1000)
    ):
        return read_snapshot(initial, "BTCUSDT", count, None,
                             lambda *args: records)



def rehash(page):
    for item in page["rows"]:
        item["dataset_fingerprint"] = _digest({
            k: v for k, v in item.items() if k != "dataset_fingerprint"
        })
    page["dataset_fingerprint"] = _digest(page["rows"])
    return page


class PartialReadFixtureTests(unittest.TestCase):
    def setUp(self):
        self.now = int(time.time() * 1000)
        self.page = fixture(self.now, count=2)
        self.assertEqual(self.page["status"], "PARTIAL")

    def test_actual_grid_producer_to_math_verified_terminan_display(self):
        result = validate_partial(self.page, "BTCUSDT", 2, now_ms=self.now)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["source_authentication"],
                         "MANAGED_TRANSPORT_ONLY_EXTERNAL_NOT_ATTESTED")
        self.assertEqual(result["coverage"]["missing_minutes"], 0)
        self.assertFalse(result["paper_admitted"])
        self.assertFalse(result["trading_authorized"])
        chart = chart_rows(result)
        self.assertEqual(len(chart), 2)
        self.assertEqual(chart[0]["o"], 2)
        self.assertLess(chart[0]["t"], chart[1]["t"])
        self.assertEqual(chart[1]["poc"], 2)

    def test_row_or_page_tamper_is_detected(self):
        mutants = []
        a = copy.deepcopy(self.page)
        a["rows"][0]["candle"]["close"] = 123
        mutants.append(a)
        a = copy.deepcopy(self.page)
        a["dataset_fingerprint"] = "0" * 64
        mutants.append(a)
        a = copy.deepcopy(self.page)
        a["rows"][0]["candle"]["close"] = 123
        mutants.append(rehash(a))  # Forged checksums cannot override Math OHLC domain
        for item in mutants:
            with self.subTest(mutant=item["dataset_fingerprint"]):
                with self.assertRaises(ValueError):
                    validate_partial(item, "BTCUSDT", 2, now_ms=self.now)

    def test_stale_gap_duplicate_revision_and_epoch_change_refused(self):
        with self.assertRaises(ValueError):
            validate_partial(self.page, "BTCUSDT", 2, now_ms=self.now + 180001)
        a = copy.deepcopy(self.page)
        a["rows"][1]["start_ms"] -= 60000
        a["rows"][1]["end_ms"] -= 60000
        a["rows"][1]["source_event_start_ms"] -= 60000
        a["rows"][1]["source_event_end_ms"] -= 60000
        a["coverage"]["expected_minutes"] = 3
        a["coverage"]["missing_minutes"] = 1
        with self.assertRaises(ValueError):
            validate_partial(rehash(a), "BTCUSDT", 2, now_ms=self.now)
        a = copy.deepcopy(self.page)
        a["rows"][1] = copy.deepcopy(a["rows"][0])
        a["dataset_fingerprint"] = _digest(a["rows"])
        with self.assertRaises(ValueError):
            validate_partial(a, "BTCUSDT", 2, now_ms=self.now)
        a = copy.deepcopy(self.page)
        a["producer_epochs"].append("other")
        with self.assertRaises(ValueError):
            validate_partial(a, "BTCUSDT", 2, now_ms=self.now)

    def test_refuse_missing_quality_source_authentication_and_authority(self):
        mutations = [
            lambda p: p.update(status="AVAILABLE"),
            lambda p: p.update(immutable=False),
            lambda p: p.update(execution_authority=True),
            lambda p: p.update(read_only=False),
            lambda p: p.update(data_quality_status="GOOD"),
            lambda p: p.update(producer="strattester"),
            lambda p: p.update(api_version={"major": 2, "minor": 0}),
            lambda p: p.update(source_revision="b" * 40),
            lambda p: p.update(symbol="ETHUSDT"),
            lambda p: p["rows"][0].update(source_identity_verified=False),
            lambda p: p["rows"][0].update(quality_status="UNKNOWN"),
            lambda p: p["rows"][0].update(quality_reasons=["missing"]),
            lambda p: p["rows"][0]["coverage"].update(exchange_completeness_attested=True),
        ]
        for mutate in mutations:
            page = copy.deepcopy(self.page)
            mutate(page)
            # Recompute both fingerprints to exercise policy beyond hash checks.
            rehash(page)
            with self.subTest(change=str(mutate)):
                with self.assertRaises(ValueError):
                    validate_partial(page, "BTCUSDT", 2, now_ms=self.now)

    def test_source_identity_is_never_converted_to_exchange_attestation(self):
        result = validate_partial(self.page, "BTCUSDT", 2, now_ms=self.now)
        self.assertNotIn("EXCHANGE_VERIFIED", str(result))
        self.assertNotIn("AVAILABLE", str(result["status"]))
        self.assertFalse(result["execution_authority"])


class Admission:
    def __init__(self):
        self.current = True

    def require_current(self):
        return self.current

    def source_identity(self, module):
        assert module == "market_data"
        return {"commit": "a" * 40}


class PartialReadRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.admission = Admission()
        self.cap = {
            "port": 29001, "token": "b" * 64,
            "source_commit": "a" * 40, "release_id": "round2",
            "epoch": "c" * 32,
        }
        self.client = data.MarketDataReadClient(self.cap, self.admission, "round2")
        self.old = data._private_market_data_client
        self.addCleanup(setattr, data, "_private_market_data_client", self.old)

    def test_unmanaged_port_cannot_admit_a_partial_chart(self):
        data._private_market_data_client = None
        with mock.patch.dict(os.environ, {"MARKET_DATA_API_PORT": "29001"}), (
                mock.patch.object(data, "_market_data_http_get",
                                  side_effect=AssertionError("NO_UNMANAGED_READ"))):
            result = data.qualified_market_data_chart("BTCUSDT")
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["rows"], [])
        self.assertFalse(result["paper_admitted"])

    def test_managed_authenticated_chart_with_read_receipt(self):
        data._private_market_data_client = self.client
        now = int(time.time() * 1000)
        page = fixture(now, count=1)
        with mock.patch.object(data, "_market_data_http_get", return_value=page) as call:
            result = data.qualified_market_data_chart("BTCUSDT", limit=1)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertFalse(result["exchange_completeness_attested"])
        self.assertFalse(result["paper_admitted"])
        self.assertFalse(result["trading_authorized"])
        self.assertEqual(result["rows"][0]["poc"], 2)
        self.assertEqual(call.call_args.args, (29001,
             "/internal/v1/candles?symbol=BTCUSDT&limit=1"))
        self.assertEqual(call.call_args.kwargs["headers"]["Authorization"],
                         "Bearer " + self.cap["token"])

    def test_revocation_after_transport_discards_data(self):
        data._private_market_data_client = self.client
        page = fixture(int(time.time() * 1000))
        def revoked(*_args, **_kwargs):
            self.admission.current = False
            return page
        with mock.patch.object(data, "_market_data_http_get", side_effect=revoked):
            self.assertEqual(data.qualified_market_data_chart("BTCUSDT", 1)["status"],
                             "UNAVAILABLE")

    def test_unqualified_and_unavailable_cannot_enable_paper(self):
        data._private_market_data_client = self.client
        page = fixture(int(time.time() * 1000))
        for change in ({"status": "UNAVAILABLE"}, {"status": "STALE"},
                       {"execution_authority": True}):
            modified = {**page, **change}
            with mock.patch.object(data, "_market_data_http_get",
                                   return_value=modified):
                response = data.qualified_market_data_chart("BTCUSDT", 1)
            self.assertEqual(response["status"], "UNAVAILABLE")
            self.assertFalse(response["paper_admitted"])
            self.assertFalse(response["execution_authority"])

    def test_http_receipt_is_readonly_no_order_or_execution_authority(self):
        from terminan.server import Handler
        data._private_market_data_client = self.client
        page = fixture(int(time.time() * 1000), count=5)
        with mock.patch.object(data, "_market_data_http_get", return_value=page), (
             mock.patch.object(Handler, "log_message", return_value=None)):
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            server.daemon_threads = True
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                connection = http.client.HTTPConnection("127.0.0.1",
                                                         server.server_port, timeout=3)
                try:
                    connection.request("GET", "/api/market-data/qualified?symbol=BTCUSDT")
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.getheader("Cache-Control"), "no-store")
                    result = json.loads(response.read())
                finally:
                    connection.close()
                self.assertEqual(result["status"], "PARTIAL")
                self.assertEqual(len(result["rows"]), 5)
                self.assertEqual(result["dataset_fingerprint"], page["dataset_fingerprint"])
                self.assertFalse(result["exchange_completeness_attested"])
                self.assertFalse(result["paper_admitted"])
                self.assertFalse(result["trading_authorized"])
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=3)

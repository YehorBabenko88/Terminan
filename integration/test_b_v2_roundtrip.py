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


    def test_old_capability_cannot_read_after_grid_restart_or_get_v1_fallback(self):
        """Real loopback Grid Handler restart, not an in-memory HTTP mock.

        This deliberately does not simulate Consul/OS process quiescence; it
        proves D cannot use the old bearer and port as a v1 fallback after
        source loss, nor treat a replacement process as the same owner.
        """
        original_server = self.server
        original_thread = self.thread
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
        replacement = ThreadingHTTPServer(("127.0.0.1", 0), read_api.Handler)
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
            self.assertNotEqual(replacement.server_port, 0)
            row = record_fixture(int(time.time() * 1000))
            with _patch.object(history_api, "immutable_minutes",
                               return_value=[row]):
                # Move the OLD client to the new listener's port, keeping its
                # original bearer: a live Grid handler must reject it.
                old_at_new_port = dict(old_capability,
                                       port=replacement.server_port)
                data._private_market_data_client = data.MarketDataReadClient(
                    old_at_new_port, self.admission, "d-round3")
                refused = data.qualified_market_data_chart("BTCUSDT", 1)
                self.assertEqual(refused["status"], "UNAVAILABLE")
                self.assertFalse(refused["paper_admitted"])
                self.assertEqual(refused["rows"], [])
                self.assertFalse(refused["execution_authority"])

                # A fresh Root-issued replacement capability is distinct,
                # chart-only and does not authorize paper or real trading.
                new_capability = dict(old_capability,
                                      port=replacement.server_port,
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

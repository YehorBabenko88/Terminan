"""Stage 8 Meta PaperEngine deterministic parity and canonical Math SDK boundary."""
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from unittest import mock

from terminan.paper import ClosedMinute, ExecutionTrade, PaperEngine

T = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)


def minute(poc="100", at=T, complete=True):
    # POC is deliberately externally supplied by the Math owner.
    return ClosedMinute(at, D(poc), complete)


def trade(seconds, price, symbol="BTCUSDT"):
    return ExecutionTrade(symbol, T + timedelta(seconds=seconds), D(price))


class PaperMigrationTests(unittest.TestCase):
    def test_short_target_matches_meta_execution_fees_and_slippage(self):
        e = PaperEngine()
        e.enabled = True
        e.on_closed_minute("BTCUSDT", minute())
        e.on_trade(trade(61, "102"))
        self.assertEqual(e.positions["BTCUSDT"].side, "short")
        result = e.on_trade(trade(62, "100"))
        self.assertEqual(result.reason, "target")
        entry = D("102") * (D(1) - D("0.0002"))
        exit_price = D("100") * (D(1) + D("0.0002"))
        size = D("100") / entry
        gross = (entry - exit_price) * size
        fees = D("100") * D("0.0006") + size * exit_price * D("0.0006")
        self.assertEqual((result.entry, result.exit, result.gross, result.fees,
                          result.net), (entry, exit_price, gross, fees,
                                        gross - fees))
        self.assertNotIn("BTCUSDT", e.positions)
        self.assertEqual(e.fills, [result])

    def test_long_stop_gap_and_slippage_match_meta_source(self):
        e = PaperEngine()
        e.enabled = True
        e.on_closed_minute("BTCUSDT", minute())
        e.on_trade(trade(60, "98"))
        result = e.on_trade(trade(62, "95"))
        self.assertEqual(result.reason, "stop")
        self.assertEqual(result.entry, D("98") * D("1.0002"))
        self.assertEqual(result.exit, D("95") * D("0.9998"))
        self.assertLess(result.net, result.gross)

    def test_no_lookahead_next_minute_and_single_position(self):
        e = PaperEngine()
        e.enabled = True
        e.on_closed_minute("BTCUSDT", minute())
        e.on_trade(trade(121, "103"))
        self.assertEqual(e.positions, {})
        e.on_trade(trade(60, "98"))
        e.on_trade(trade(61, "97.9"))
        self.assertEqual(len(e.positions), 1)
        self.assertEqual(len(e.fills), 0)

    def test_unclosed_minute_and_gap_fence_new_entries(self):
        e = PaperEngine()
        e.enabled = True
        e.on_closed_minute("BTCUSDT", minute())
        e.on_closed_minute("BTCUSDT", minute(complete=False))
        e.on_trade(trade(61, "103"))
        self.assertEqual(e.positions, {})
        e.on_closed_minute("BTCUSDT", minute())
        e.on_gap("BTCUSDT")
        e.on_trade(trade(61, "103"))
        self.assertEqual(e.positions, {})

    def test_disabled_default_and_invalid_prices_refused(self):
        e = PaperEngine()
        e.on_closed_minute("BTCUSDT", minute())
        e.on_trade(trade(61, "103"))
        self.assertEqual(e.positions, {})
        e.enabled = True
        for p in ("NaN", "Infinity", "0", "-1"):
            with self.subTest(price=p):
                with self.assertRaises(ValueError):
                    e.on_trade(trade(61, p))
        with self.assertRaises(ValueError):
            e.on_closed_minute("BTCUSDT", minute("NaN"))
        with self.assertRaises(ValueError):
            PaperEngine(notional=D("-1"))

    def test_math_sdk_compute_batch_is_real_consumer_not_local_poc_copy(self):
        request = {
            "schema": "math.market.compute.v1",
            "execution_authority": False,
            "source": {"snapshot_sha256": "a" * 64, "as_of_ms": 1,
                       "units": {"price": "quote/base", "volume": "base"}},
            "operations": [{"operation": "volume_profile_poc",
                            "input": {"profile": [
                                {"price": "100", "volume": "3"},
                                {"price": "101", "volume": "3"}],
                                "close": "101"}}],
        }
        calls = []
        def sdk(value):
            calls.append(value)
            return {
                "schema": "math.market.result.v1",
                "execution_authority": False,
                "trading_authorized": False,
                "provenance": "CALLER_SUPPLIED_UNATTESTED",
                "source": request["source"],
                "results": [{"operation": "volume_profile_poc",
                             "value": "101"}],
            }
        module = types.ModuleType("market_compute_api")
        module.compute_batch = sdk
        e = PaperEngine()
        with mock.patch.dict(sys.modules, {"market_compute_api": module}):
            e.on_math_closed_minute("BTCUSDT", T, request)
        self.assertEqual(calls, [request])
        self.assertEqual(e.reference["BTCUSDT"], (T, D("101")))

    def test_math_unattested_result_never_grants_live_authority(self):
        request = {
            "schema": "math.market.compute.v1", "execution_authority": False,
            "source": {"snapshot_sha256": "a" * 64, "as_of_ms": 1,
                       "units": {"price": "quote/base", "volume": "base"}},
            "operations": [{"operation": "volume_profile_poc",
                            "input": {"profile": [], "close": "100"}}],
        }
        e = PaperEngine()
        with self.assertRaises(ValueError):
            e.on_math_closed_minute(
                "BTCUSDT", T, request,
                compute=lambda req: {"schema": "math.market.result.v1",
                                     "trading_authorized": True,
                                     "results": [{"operation": "volume_profile_poc",
                                                  "value": "100"}]},
            )
        self.assertEqual(e.reference, {})
        with self.assertRaises(ValueError):
            e.on_math_closed_minute("BTCUSDT", T,
                                    {**request, "execution_authority": True},
                                    compute=lambda _: None)
        self.assertEqual(e.reference, {})


if __name__ == "__main__":
    unittest.main()

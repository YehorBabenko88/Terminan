"""Stage 8 Meta PaperEngine deterministic parity and canonical Math SDK boundary."""
import http.client
import json
import sys
import threading
import types
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from unittest import mock

from terminan.paper import (ClosedMinute, ExecutionTrade, PaperEngine,
                            STRATEGIES, replay_paper)

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
        with self.assertRaises(ValueError):
            e.on_trade(trade(60, "98"))
        e = PaperEngine()
        e.enabled = True
        e.on_closed_minute("BTCUSDT", minute())
        e.on_trade(trade(60, "98"))
        e.on_trade(trade(61, "97.9"))
        self.assertEqual(len(e.positions), 1)
        self.assertEqual(len(e.fills), 0)

    def test_out_of_order_closed_minute_is_rejected(self):
        e = PaperEngine()
        e.on_closed_minute("BTCUSDT", minute(at=T + timedelta(minutes=1)))
        with self.assertRaises(ValueError):
            e.on_closed_minute("BTCUSDT", minute())
        self.assertEqual(e.reference["BTCUSDT"][0], T + timedelta(minutes=1))

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


def offline_request():
    start_ms = int(T.timestamp() * 1000)
    return {
        "schema": "terminan.paper.replay.v2",
        "run_id": "offline-001",
        "source": {
            "snapshot_sha256": "a" * 64,
            "as_of_ms": start_ms + 120000,
            "units": {"price": "quote/base", "volume": "base"},
        },
        "parameters": {},
        "events": [
            {
                "kind": "closed_minute", "event_ms": start_ms + 60000,
                "symbol": "BTCUSDT",
                "profile": [{"price": "100", "volume": "1"}], "close": "100",
            },
            {
                "kind": "trade", "event_ms": start_ms + 61000,
                "symbol": "BTCUSDT", "price": "102",
            },
            {
                "kind": "trade", "event_ms": start_ms + 62000,
                "symbol": "BTCUSDT", "price": "100",
            },
        ],
    }


def mock_math(request):
    return {
        "schema": "math.market.result.v1",
        "execution_authority": False,
        "trading_authorized": False,
        "provenance": "CALLER_SUPPLIED_UNATTESTED",
        "source": request["source"],
        "results": [{"operation": "volume_profile_poc", "value": "100"}],
    }


class OfflinePaperApiTests(unittest.TestCase):
    def test_single_registry_object_used_for_offline_executor(self):
        from terminan.contracts import StrategyRegistry
        self.assertIsInstance(STRATEGIES, StrategyRegistry)
        registered = STRATEGIES.discover()
        self.assertEqual(len(registered), 2)
        self.assertTrue(all(item.implementation is PaperEngine for item in registered))
        self.assertIs(registered[0].implementation, PaperEngine)
        self.assertEqual(registered[0].id, "poc_next_minute")
        explicit = offline_request()
        explicit["strategy"] = {
            "id": registered[0].id, "version": registered[0].version
        }
        result = replay_paper(explicit, compute=mock_math)
        self.assertEqual(result["strategy"]["version"], "2")
        self.assertEqual(len(result["fills"]), 1)

    def test_replay_has_stable_digest_and_no_order_authority(self):
        request = offline_request()
        first = replay_paper(request, compute=mock_math)
        second = replay_paper(request, compute=mock_math)
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], "terminan.paper.result.v2")
        self.assertEqual(first["strategy"]["id"], "poc_next_minute")
        self.assertEqual(first["strategy"]["version"], "2")
        self.assertEqual(len(first["strategy"]["fingerprint"]), 64)

        self.assertEqual(first["status"], "OFFLINE_UNATTESTED")
        self.assertFalse(first["trading_authorized"])
        self.assertFalse(first["execution_authority"])
        self.assertEqual(first["events_processed"], 3)
        self.assertEqual(len(first["fills"]), 1)
        self.assertEqual(first["fills"][0]["reason"], "target")
        self.assertEqual(first["open_positions"], {})
        self.assertEqual(len(first["result_sha256"]), 64)

    def test_reject_bad_source_order_symbol_or_input(self):
        base = offline_request()
        invalid = [
            {**base, "schema": "terminan.live.order.v1"},
            {**base, "source": {**base["source"], "snapshot_sha256": "short"}},
            {**base, "events": [base["events"][2], base["events"][0]]},
            {**base, "events": [{**base["events"][1], "symbol": "../ETH"}]},
            {**base, "events": [{**base["events"][0], "event_ms":
                                base["events"][0]["event_ms"] + 1}]},
            {**base, "events": [base["events"][0]] * 1025},
            {**base, "parameters": {"live_orders": "true"}},
            {**base, "strategy": {"id": "unapproved", "version": "1"}},
            {**base, "strategy": {"id": "poc_next_minute",
                                  "version": "unreviewed"}},
            {**base, "strategy": {"id": "poc_next_minute",
                                  "version": "2", "orders": True}},

        ]
        for request in invalid:
            with self.subTest(case=str(request)[:90]):
                with self.assertRaises(ValueError):
                    replay_paper(request, compute=mock_math)

    def test_single_existing_terminal_renders_offline_paper_route(self):
        from importlib.resources import files
        html = files("terminan").joinpath("index.html").read_text(
            encoding="utf-8")
        for marker in ("id=\"paperinput\"", "id=\"paperrun\"",
                       "/api/paper/replay", "OFFLINE / UNATTESTED"):
            self.assertIn(marker, html)
        self.assertNotIn("submitOrder(", html)
        self.assertNotIn("createOrder(", html)

    def test_same_origin_http_paper_replay_and_forbidden_order_endpoint(self):
        from http.server import ThreadingHTTPServer
        from terminan.server import Handler

        module = types.ModuleType("market_compute_api")
        module.compute_batch = mock_math
        with mock.patch.dict(sys.modules, {"market_compute_api": module}):
            with mock.patch.object(Handler, "log_message", return_value=None):
                server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
                server.daemon_threads = True
                worker = threading.Thread(target=server.serve_forever,
                                          daemon=True)
                worker.start()
                try:
                    def post(path, payload, *, origin=None):
                        conn = http.client.HTTPConnection(
                            "127.0.0.1", server.server_port, timeout=3)
                        headers = {"Content-Type": "application/json"}
                        if origin is not None:
                            headers["Origin"] = origin
                        try:
                            conn.request("POST", path, body=json.dumps(payload),
                                         headers=headers)
                            response = conn.getresponse()
                            return response.status, json.loads(response.read()) \
                                if response.status != 404 else None
                        finally:
                            conn.close()
                    status, response = post("/api/paper/replay", offline_request())
                    self.assertEqual(status, 200)
                    self.assertEqual(response["status"], "OFFLINE_UNATTESTED")
                    self.assertEqual(len(response["fills"]), 1)
                    rejected, _ = post("/api/paper/replay", offline_request(),
                                       origin="http://attacker.invalid")
                    self.assertEqual(rejected, 400)
                    not_found, _ = post("/api/orders", offline_request())
                    self.assertEqual(not_found, 404)
                finally:
                    server.shutdown()
                    server.server_close()
                    worker.join(timeout=3)
                    self.assertFalse(worker.is_alive())


class TradingSizingOwnershipTests(unittest.TestCase):
    """Pinned Math history_sizing execution policy before owner cutover."""

    @staticmethod
    def rows():
        return [
            {"signal_id": "a", "pnl": -2.0, "fees": .2, "slippage": .1,
             "mfe": 4, "mae": -3},
            {"signal_id": "b", "pnl": -1.0, "fees": .2, "slippage": .1,
             "mfe": 2, "mae": -1},
            {"signal_id": "c", "pnl": 3.0, "fees": .2, "slippage": .1,
             "mfe": 5, "mae": -1},
            {"signal_id": "d", "pnl": 4.0, "fees": .2, "slippage": .1},
        ]

    def test_fixed_policy_is_original_identity(self):
        from terminan.paper import apply_sizing
        rows = self.rows()
        actual = apply_sizing(rows)
        self.assertEqual(rows, [
            {k: v for k, v in row.items()} for row in self.rows()
        ])
        self.assertEqual([row["size_multiplier"] for row in actual], [1.] * 4)
        self.assertEqual([row["pnl"] for row in actual], [-2., -1., 3., 4.])

    def test_martingale_loss_streak_matches_pinned_policy(self):
        from terminan.paper import apply_sizing
        rows = apply_sizing(self.rows(), "MARTINGALE",
                            base_size=1, multiplier=2, max_steps=3, max_size=4)
        self.assertEqual([row["size_multiplier"] for row in rows], [1, 2, 4, 1])
        self.assertEqual([row["pnl"] for row in rows], [-2., -2., 12., 4.])
        self.assertEqual([row["fees"] for row in rows], [.2, .4, .8, .2])
        self.assertEqual([row["slippage"] for row in rows], [.1, .2, .4, .1])

    def test_antimartingale_win_streak_matches_pinned_policy(self):
        from terminan.paper import apply_sizing
        rows = [
            {"pnl": 1., "fees": 0., "slippage": 0.},
            {"pnl": 2., "fees": 0., "slippage": 0.},
            {"pnl": -1., "fees": 0., "slippage": 0.},
            {"pnl": 1., "fees": 0., "slippage": 0.},
        ]
        sized = apply_sizing(rows, "ANTI_MARTINGALE", max_size=4)
        self.assertEqual([r["size_multiplier"] for r in sized], [1, 2, 4, 1])
        with self.assertRaises(ValueError):
            apply_sizing(rows, mode="UNKNOWN")

    def test_equity_and_ruin_original_thresholds(self):
        from terminan.paper import ruin_stats
        from market_math import paper_net_pnl
        rows = self.rows()
        self.assertAlmostEqual(paper_net_pnl(rows[0].get('pnl',0),rows[0].get('fees',0),rows[0].get('slippage',0)), -2.3)
        report = ruin_stats(rows, starting_equity=10, ruin_fraction=.5)
        value = 10.0
        peak = value
        minimum = value
        max_drawdown = 0.0
        ruined = False
        for row in rows:
            value += float(row["pnl"]) - float(row["fees"]) - float(row["slippage"])
            peak = max(peak, value)
            minimum = min(minimum, value)
            max_drawdown = max(max_drawdown, peak - value)
            ruined |= value <= 5.0
        self.assertEqual(report, {
            "ending_equity": value, "min_equity": minimum,
            "max_drawdown": max_drawdown, "ruin_threshold": 5.0,
            "ruined": ruined,
        })

    def test_old_source_import_never_required(self):
        from terminan import paper
        from terminan.contracts import StrategyRegistry
        self.assertIsInstance(paper.STRATEGIES, StrategyRegistry)
        self.assertTrue(callable(paper.apply_sizing))
        self.assertTrue(callable(paper.ruin_stats))
        self.assertFalse(hasattr(paper,'trade_net_pnl'))

    def test_trade_accounting_refuses_nonfinite_inputs_and_overflow(self):
        from terminan.paper import apply_sizing, ruin_stats
        from market_math import paper_net_pnl

        for field in ("pnl", "fees", "slippage"):
            for invalid in ("NaN", "Infinity", float("-inf")):
                row = dict(pnl=4.0, fees=0.2, slippage=0.1)
                row[field] = invalid
                with self.subTest(field=field, invalid=invalid):
                    with self.assertRaises(ValueError):
                        paper_net_pnl(row.get('pnl',0),row.get('fees',0),row.get('slippage',0))
        with self.assertRaises(ValueError):
            paper_net_pnl(1e308,-1e308,0)
        for trades, params in (([{"pnl": 1}], {"base_size": float("nan")}),
                               ([{"pnl": 1}], {"base_size": float("inf")}),
                               ([{"pnl": -1}], {"mode": "MARTINGALE", "max_steps": float("inf")}),
                               ([{"pnl": 1, "mae": 1e308}], {"base_size": 2}),
                               ([{"pnl": 1e308}], {"base_size": 2})):
            with self.subTest(trades=trades, params=params), self.assertRaises(ValueError):
                apply_sizing(trades, **params)
        for trades, params in (([], {"starting_equity": float("inf")}),
                               ([], {"starting_equity": 1e308, "ruin_fraction": 2}),
                               ([{"pnl": 1e308}], {"starting_equity": 1e308}),
                               ([{"pnl": -1e308}, {"pnl": -1e308}],
                                {"starting_equity": 1e308})):
            with self.subTest(trades=trades, params=params), self.assertRaises(ValueError):
                ruin_stats(trades, **params)


if __name__ == "__main__":
    unittest.main()

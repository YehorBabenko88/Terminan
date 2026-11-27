"""D ROUND35: executable, fail-closed G012 differential against original D129.

Original D129's 68-line function and original Math D167 are imported from
immutable SHA-pinned, byte-verified test-only checkouts. Current B Grid,
canonical Math and D qualified consumer are executed unmodified. Synthetic
stored minute records only: no SQL, provider, live trades or authorization.
This limited parity test NEVER authorizes legacy retirement.
"""
import ast
import copy
from decimal import Decimal
from hashlib import sha1
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

for key in ("ROUND3_MATH_SOURCE", "ROUND3_GRID_SOURCE"):
    source = os.environ.get(key)
    if not source or not os.path.isabs(source):
        raise RuntimeError("PINNED_ROUND3_SOURCE_REQUIRED")
    sys.path.insert(0, source)

from market_data.provenance import digest, minute_record, producer
from market_data_v2.qualified_read_contract import ProvenanceReadError
from market_data_v2.read_api import qualified_rollup_snapshot
from market_math import exact_sum, executed_volume_delta
from terminan.qualified_rollup import (
    chart_rollup_rows, validate_qualified_rollup,
)

ROOT = Path(__file__).resolve().parents[1]
OLD_D = ROOT / "upstream" / "terminan-d129" / "terminan" / "qualified_partial.py"
OLD_MATH = ROOT / "upstream" / "math-d167" / "python" / "market_math.py"
OLD_D_BLOB = "27cd754b97a0a8c32b0ec51daac41110dca35292"
OLD_MATH_BLOB = "aebe6f799ffe2c20c9b68daad10b96764c245246"
NOW = (1800000120000 // 900000) * 900000 + 45000
BOUNDARY = (NOW // 900000) * 900000


def original_blob(path, expected):
    raw = path.read_bytes()
    oid = sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
    if oid != expected:
        # Windows checkout can materialize CRLF from immutable Git LF bytes.
        # Recompute and REQUIRE the identical pinned Git blob after LF
        # normalization; a different source still fails closed.
        lf = raw.replace(b"\r\n", b"\n")
        lf_oid = sha1(b"blob " + str(len(lf)).encode("ascii") + b"\0" + lf).hexdigest()
        if lf == raw or lf_oid != expected:
            raise AssertionError("ORIGINAL_G012_BLOB_MISMATCH: " + path.name)
        return lf
    return raw


def original_aggregator():
    source = original_blob(OLD_D, OLD_D_BLOB).decode("utf-8")
    original_blob(OLD_MATH, OLD_MATH_BLOB)
    module = ast.parse(source, filename=str(OLD_D))
    functions = [node for node in module.body
                 if isinstance(node, ast.FunctionDef)
                 and node.name == "qualified_timeframe_rows"]
    if len(functions) != 1:
        raise AssertionError("ORIGINAL_G012_FUNCTION_MISSING")
    constants = {}
    for node in module.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in (
                "_MTF_WINDOWS", "_MTF_MAX_SOURCE_ROWS", "_MTF_MAX_BARS"
            ):
                constants[target.id] = ast.literal_eval(node.value)
    if len(constants) != 3:
        raise AssertionError("ORIGINAL_G012_CONSTANTS_MISSING")
    namespace = {"__builtins__": __builtins__, **constants}
    exec(compile(ast.Module(body=functions, type_ignores=[]),
                 str(OLD_D), "exec"), namespace)
    spec = importlib.util.spec_from_file_location("d_original_math_d167", OLD_MATH)
    if spec is None or spec.loader is None:
        raise AssertionError("ORIGINAL_G012_MATH_UNAVAILABLE")
    old_math = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old_math)
    if not hasattr(old_math, "aggregate_closed_minute_ohlcv"):
        raise AssertionError("ORIGINAL_G012_MATH_KERNEL_MISSING")
    return namespace["qualified_timeframe_rows"], old_math


def minute_rows(width, buy, sell):
    source = producer("d-r35-synthetic", "a" * 40,
                      "wss://stream.bybit.com/v5/public/linear")
    first = BOUNDARY - width * 60000
    result = []
    for i in range(width):
        start = first + i * 60000
        row = dict(
            symbol="BTCUSDT", start_ms=start,
            source_event_start_ms=start + 1,
            source_event_end_ms=start + 59000,
            source_provenance=source,
            open=1.0, high=2.0, low=1.0, close=2.0,
            buy_volume=buy, sell_volume=sell, delta=buy-sell,
            trade_count=2, poc_price=2.0,
            quality_status="GOOD", quality_reasons=[],
            levels=[dict(price=2.0, buy_volume=buy, sell_volume=sell,
                         delta=buy-sell, volume=buy+sell,
                         buy_count=1, sell_count=1)],
        )
        record = minute_record(row, NOW, "d-r35-synthetic")
        if record["status"] != "PARTIAL":
            raise AssertionError("INVALID_ORIGINAL_MINUTE_FIXTURE")
        result.append(record)
    return result


def legacy_receipt(rows):
    width = len(rows)
    return dict(
        status="PARTIAL", chart_read_only=True,
        execution_authority=False, paper_admitted=False,
        trading_authorized=False,
        source_authenticity="NOT_INDEPENDENTLY_ATTESTED",
        record_integrity="VERIFIED",
        rows=tuple(copy.deepcopy(rows)),
        coverage=dict(expected_minutes=width, observed_minutes=width,
                      missing_minutes=0),
        dataset_fingerprint=digest(rows),
        freshness_utc_ms=NOW,
    )


class OriginalD129AgainstCanonicalGridAndD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original, cls.old_math = original_aggregator()
        cls.old_aggregate = staticmethod(original)

    def legacy(self, rows, timeframe, bars):
        with patch.dict(sys.modules, {"market_math": self.old_math}):
            return self.old_aggregate(legacy_receipt(rows), timeframe,
                                      max_bars=bars)

    def canonical(self, rows, timeframe, bars):
        envelope = qualified_rollup_snapshot(
            "BTCUSDT", timeframe, bars, before_ms=BOUNDARY,
            reader=lambda *_: copy.deepcopy(rows), now_ms=NOW, exact=True)
        validated = validate_qualified_rollup(
            envelope, "BTCUSDT", timeframe, bars,
            now_ms=NOW, exact=True)
        return envelope, chart_rollup_rows(validated)

    def test_original_68_line_volume_ohlcv_clock_matches_grid_math_and_d(self):
        for timeframe, step in (("5m", 5), ("15m", 15)):
            for bars in (1, 2):
                for buy, sell in ((0.1, 0.3), (1.0, 0.5)):
                    with self.subTest(timeframe=timeframe, bars=bars,
                                      buy=buy, sell=sell):
                        rows = minute_rows(step * bars, buy, sell)
                        old = self.legacy(rows, timeframe, bars)
                        envelope, new = self.canonical(rows, timeframe, bars)
                        self.assertEqual(old["status"], "PARTIAL")
                        self.assertEqual(envelope["status"], "PARTIAL")
                        self.assertEqual(old["coverage"], envelope["coverage"])
                        self.assertEqual(old["source_minutes"],
                                         envelope["source_minutes"])
                        self.assertEqual(len(old["rows"]), len(new))
                        for earlier, current in zip(old["rows"], new):
                            for old_key, new_key in (
                                ("o", "o"), ("h", "h"),
                                ("l", "l"), ("c", "c"), ("v", "v")
                            ):
                                self.assertEqual(Decimal(earlier[old_key]),
                                                 Decimal(str(current[new_key])))
                            self.assertEqual(earlier["t"], current["t"])
                            self.assertEqual(earlier["closed_at_ms"],
                                             current["closed_at_ms"])
                            self.assertEqual(
                                Decimal(current["delta_decimal"]),
                                executed_volume_delta(
                                    Decimal(current["buy_volume_decimal"]),
                                    Decimal(current["sell_volume_decimal"])))
                            self.assertEqual(
                                Decimal(current["volume_decimal"]),
                                exact_sum((
                                    Decimal(current["buy_volume_decimal"]),
                                    Decimal(current["sell_volume_decimal"]))))
                        for key in ("paper_admitted", "trading_authorized",
                                    "execution_authority"):
                            self.assertIs(old[key], False)
                            self.assertIs(envelope[key], False)
                        self.assertEqual(envelope["exchange_completeness"],
                                         "NOT_ATTESTED")
                        self.assertEqual(envelope["source_authenticity"],
                                         "NOT_INDEPENDENTLY_ATTESTED")

    def test_missing_interior_minute_refused_by_both_original_paths(self):
        for timeframe, step in (("5m", 5), ("15m", 15)):
            rows = minute_rows(step, 1.0, 0.5)
            broken = rows[:2] + rows[3:]
            with self.subTest(timeframe=timeframe):
                with self.assertRaises(ValueError):
                    self.legacy(broken, timeframe, 1)
                with self.assertRaises(ProvenanceReadError):
                    self.canonical(broken, timeframe, 1)

    def test_rehashed_negative_zero_delta_and_authority_never_fallback(self):
        rows = minute_rows(5, 1.0, 0.5)
        envelope, _ = self.canonical(rows, "5m", 1)
        for change in ("signed_zero", "false_authority", "wrong_status"):
            forged = copy.deepcopy(envelope)
            if change == "signed_zero":
                forged["rows"][0]["delta_decimal"] = "-0"
            elif change == "false_authority":
                forged["paper_admitted"] = True
            else:
                forged["status"] = "QUALIFIED"
            forged["dataset_fingerprint"] = digest({
                key: value for key, value in forged.items()
                if key != "dataset_fingerprint"
            })
            with self.subTest(change=change), self.assertRaisesRegex(
                ValueError, "QUALIFIED_ROLLUP_UNAVAILABLE"
            ):
                validate_qualified_rollup(
                    forged, "BTCUSDT", "5m", 1, now_ms=NOW,
                    exact=True)


if __name__ == "__main__":
    unittest.main()

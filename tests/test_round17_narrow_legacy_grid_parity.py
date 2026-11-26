"""Round17 narrow original BacktestEngine vs one canonical PaperEngine.

A historical source is executed from SHA-pinned archived AST nodes under
tests ONLY. This tests an exact-open subset, not the historical 28-variant
strategy or real bid/ask executable orders. All other historical descriptors
and nonqualified cases stay SPEC_ONLY.
"""
import ast
from dataclasses import dataclass
from decimal import Decimal as D
from hashlib import sha1
import heapq
import math
from pathlib import Path
from typing import Dict,List,Optional,Tuple
import unittest

from terminan.legacy_level_base_research import propose_legacy_level_base
from terminan.research_signals import ResearchBar,ResearchSignal
from terminan.paper import PaperEngine

_SOURCE=Path(__file__).resolve().parent/'fixtures'/'d_round13_strattester'/'legacy_grid.py'
_BLOB='87a7ea0fa5b66b2faeb2e8be45efa183cbc16ccd'
_CLASSES=frozenset(('BacktestConfig','MinuteCandle','LevelSeed','Level','EngineTrade','BacktestEngine'))


def _historical_executable():
    raw=_SOURCE.read_bytes()
    assert sha1(b'blob '+str(len(raw)).encode('ascii')+b'\0'+raw).hexdigest()==_BLOB
    parsed=ast.parse(raw.decode('utf-8'),filename=str(_SOURCE))
    selected=[node for node in parsed.body if isinstance(node,ast.ClassDef)
              and node.name in _CLASSES]
    assert {node.name for node in selected}==_CLASSES
    namespace=dict(dataclass=dataclass,heapq=heapq,math=math,
                   Optional=Optional,Dict=Dict,List=List,Tuple=Tuple)
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(_SOURCE),'exec'),namespace)
    return namespace


def _bar(t,o,h,l,c):
    return ResearchBar(t,D(str(o)),D(str(h)),D(str(l)),D(str(c)))


class LegacyLevelConstrainedRound17(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.historical=_historical_executable()

    def test_historical_source_exact_blob_and_no_duplicate_engine_in_runtime(self):
        raw=_SOURCE.read_bytes()
        self.assertEqual(sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),_BLOB)
        import inspect
        import terminan.legacy_level_base_research as canonical
        src=inspect.getsource(canonical)
        self.assertNotIn('class BacktestEngine',src)
        self.assertNotIn('class PaperEngine',src)
        self.assertIn('paper_stop_price(',src)

    def test_exact_open_long_short_historical_vs_one_paper_engine(self):
        h=self.historical
        for variant,level,rows in (
            ('HIGH_BASE',100,((60000,99.5,100,99,99.7),
                              (120000,99.7,102,99.6,101))),
            ('LOW_BASE',100,((60000,100.5,101,100,100.4),
                             (120000,100.4,101,98,99))),
        ):
            with self.subTest(variant=variant):
                cfg=h['BacktestConfig'](allowed_level_types=(
                    ('HIGH',) if variant=='HIGH_BASE' else ('LOW',)))
                old=h['BacktestEngine']('BTCUSDT',cfg)
                label='HIGH' if variant=='HIGH_BASE' else 'LOW'
                old.add_level(h['LevelSeed']('1H',label,float(level),0,0))
                for row in rows:
                    old.process_minute(h['MinuteCandle'](*row))
                old.close_end_of_data()
                self.assertEqual(len(old.closed_trades),1)
                historical=old.closed_trades[0]
                first=_bar(*rows[0])
                candidate=propose_legacy_level_base(
                    'BTCUSDT',variant,D(str(level)),0,first,
                    bar_ms=60000,as_of_ms=180000)
                self.assertEqual(candidate.side,
                                 'long' if variant=='HIGH_BASE' else 'short')
                self.assertFalse(candidate.trading_authorized)
                self.assertEqual(candidate.observed_at_ms,120000)
                self.assertFalse(hasattr(candidate,'signal'))
                self.assertFalse(candidate.execution_authority)
                self.assertEqual(candidate.equivalence_scope,
                                 'RETROSPECTIVE_EXACT_OPEN_NO_ENTRY_BAR_EXIT_V2')
                self.assertAlmostEqual(float(candidate.entry_price),
                                       historical.entry_price,places=9)
                self.assertAlmostEqual(float(candidate.stop),
                                       historical.stop_loss,places=9)
                self.assertAlmostEqual(float(candidate.target),
                                       historical.take_profit,places=9)
                # RETROSPECTIVE comparison ONLY: test constructs the historical
                # hypothetical pre-open signal. Production MUST NOT emit it.
                # Offline model is the ONE existing canonical PaperEngine.
                engine=PaperEngine(notional=D('100'),fee_rate=D('0.00055'),
                                   slippage_bps=D('0'))
                self.assertFalse(engine.enabled)
                engine.enabled=True
                result=engine.execute_signal(
                    ResearchSignal('BTCUSDT',0,candidate.side,'limit',
                                   candidate.entry_price,candidate.stop,candidate.target),
                    tuple(_bar(*v) for v in rows),
                    bar_ms=60000,as_of_ms=180000,
                    ambiguity_policy='SL_FIRST')
                self.assertEqual((result.entry_ms,result.exit_ms),
                                 (historical.entry_time,historical.exit_time))
                self.assertEqual(historical.exit_reason,'TP')
                self.assertEqual(result.fill.reason,'target')
                self.assertAlmostEqual(float(result.fill.entry),
                                       historical.entry_price,places=9)
                self.assertAlmostEqual(float(result.fill.exit),
                                       historical.exit_price,places=9)
                self.assertAlmostEqual(float(result.fill.gross),
                                       historical.gross_pnl,places=8)
                self.assertAlmostEqual(float(result.fill.fees),
                                       historical.entry_fee+historical.exit_fee,
                                       places=8)
                self.assertAlmostEqual(float(result.fill.net),
                                       historical.net_pnl,places=8)

    def test_ordinary_stop_like_breakout_must_not_be_mispriced_as_limit(self):
        h=self.historical
        cfg=h['BacktestConfig'](allowed_level_types=('HIGH',))
        old=h['BacktestEngine']('BTCUSDT',cfg)
        old.add_level(h['LevelSeed']('1H','HIGH',100.0,0,0))
        row=(60000,99.4,99.8,99.2,99.6)
        old.process_minute(h['MinuteCandle'](*row))
        self.assertEqual(len(old.open_positions),1)
        old_entry=next(iter(old.open_positions.values())).entry_price
        self.assertAlmostEqual(old_entry,99.5,places=9)
        # Canonical LIMIT would fill at favorable open=99.4 (NOT original
        # trigger=99.5). Explicit rejection prevents false legacy parity.
        with self.assertRaisesRegex(ValueError,'TRIGGER_MUST_EQUAL_OPEN'):
            propose_legacy_level_base(
                'BTCUSDT','HIGH_BASE',D('100'),0,_bar(*row),
                bar_ms=60000,as_of_ms=120000)

    def test_intrabar_exits_and_unknown_source_are_refused(self):
        with self.assertRaisesRegex(ValueError,'ENTRY_BAR_EXIT_UNRESOLVED'):
            propose_legacy_level_base(
                'BTCUSDT','HIGH_BASE',D('100'),0,
                _bar(60000,99.5,101,98,99.5),
                bar_ms=60000,as_of_ms=120000)
        with self.assertRaises(ValueError):
            propose_legacy_level_base(
                'BTCUSDT','LOW_BASE',D('100'),0,
                _bar(60000,100.6,101,100,100.4),
                bar_ms=60000,as_of_ms=120000)
        with self.assertRaises(ValueError):
            propose_legacy_level_base(
                'BTCUSDT','LEVEL_BASE',D('100'),0,
                _bar(60000,99.5,100,99,99.7),
                bar_ms=60000,as_of_ms=120000)
        with self.assertRaises(ValueError):
            propose_legacy_level_base(
                'BTCUSDT','HIGH_BASE',D('100'),0,
                _bar(0,99.5,100,99,99.7),
                bar_ms=60000,as_of_ms=120000)

    def test_no_source_authentication_spread_or_execution_rights(self):
        item=propose_legacy_level_base(
            'BTCUSDT','HIGH_BASE',D('100'),0,
            _bar(60000,99.5,100,99,99.7),
            bar_ms=60000,as_of_ms=120000)
        self.assertEqual(item.source_authentication,'NOT_EVALUATED')
        self.assertEqual(item.observed_at_ms,120000)
        self.assertFalse(hasattr(item,'signal'))
        self.assertFalse(hasattr(item,'decision_ms'))
        self.assertEqual(item.availability_basis,'FULL_ENTRY_BAR_CLOSE_DECLARED_NOT_AUTHENTICATED')
        self.assertFalse(PaperEngine().enabled)
        self.assertFalse(item.trading_authorized)
        # No quote book exists in an OHLC; spread, L2, tick path and live
        # fill authority cannot be assumed. Nonzero slippage changes outputs.


if __name__=='__main__':
    unittest.main()

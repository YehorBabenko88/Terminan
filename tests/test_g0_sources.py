from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from terminan import g0_sources as sources

ROOT = Path(__file__).resolve().parents[1]

@contextmanager
def connection(path):
    con=sqlite3.connect(path)
    try:
        with con: yield con
    finally: con.close()

class SourceContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'synthetic.sqlite'
        upstream = Path(os.environ.get('STRATTESTER_REPO', ROOT.parent/'strattester'))
        spec = importlib.util.spec_from_file_location('pinned_schema', upstream/'strattester/marketdata/schema.py')
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        with connection(self.path) as con:
            con.executescript(mod.SCHEMA_SQL)
            con.execute("INSERT INTO schema_meta VALUES('schema_version',?)", (str(mod.SCHEMA_VERSION),))
            con.executemany('INSERT INTO candles(symbol,timeframe,open_time,open,high,low,close,volume,complete) VALUES(?,?,?,?,?,?,?,?,?)',
                            [('BTCUSDT','1m',t,10,12,9,11,5,1) for t in (0,60000,180000)])
        self.env = patch.dict(os.environ, {'TERMINAN_STRATTESTER_DB':str(self.path),'TERMINAN_RESULTS_DB':'','TERMINAN_GRID_DSN':''})
        self.env.start(); self.addCleanup(self.env.stop)

    def test_actual_pinned_schema_gap_stale_and_read_only(self):
        before = self.path.read_bytes()
        view = sources.snapshot('strattester','BTCUSDT',now_ms=1000000)
        self.assertEqual(view['state'],'STALE')
        self.assertEqual(view['coverage']['missing_intervals'],1)
        self.assertEqual(view['rows'][1]['t'],60000)
        self.assertEqual(view['authority'],'HISTORICAL_ONLY')
        self.assertEqual(view['schema_version'],2)
        self.assertEqual(self.path.read_bytes(),before)

    def test_schema_mismatch_and_missing_file_are_distinct(self):
        with connection(self.path) as con:
            con.execute("UPDATE schema_meta SET value='99'")
        self.assertEqual(sources.snapshot('strattester','BTCUSDT')['state'],'SCHEMA_MISMATCH')
        self.path.unlink()
        self.assertEqual(sources.snapshot('strattester','BTCUSDT')['state'],'UNAVAILABLE')
        self.assertFalse(self.path.exists())

    def test_invalid_source_values_fail_closed(self):
        for value in (-1,1.5,'bad'):
            with self.subTest(value=value):
                with connection(self.path) as con:
                    con.execute('UPDATE candles SET open_time=? WHERE open_time=(SELECT min(open_time) FROM candles)',(value,))
                result=sources.snapshot('strattester','BTCUSDT')
                self.assertEqual(result['state'],'INVALID_DATA'); self.assertEqual(result['rows'],[])

    def test_symbol_validation_even_when_disconnected(self):
        with self.assertRaises(ValueError): sources.snapshot('grid','BTCUSDT;DROP')

    def test_partial_sources_and_no_credentials_in_errors(self):
        with patch.dict(os.environ,{'TERMINAN_GRID_DSN':'postgresql://secret:password@private/db'}):
            with patch.object(sources,'grid_rows',side_effect=RuntimeError('secret password private')):
                result=sources.all_sources('BTCUSDT')
        self.assertEqual(result['state'],'PARTIAL')
        self.assertNotIn('password',json.dumps(result)); self.assertNotIn(str(self.path),json.dumps(result))

    def test_research_uses_seconds_to_utc_ms_and_no_live_authority(self):
        with connection(self.path) as con:
            con.execute('CREATE TABLE research_results(run_id TEXT,symbol TEXT,strategy_id TEXT,strategy_version TEXT,created_at REAL,metrics TEXT)')
            con.execute("INSERT INTO research_results VALUES('r','BTCUSDT','s','1',123.5,'{}')")
        with patch.dict(os.environ,{'TERMINAN_RESULTS_DB':str(self.path)}):
            result=sources.snapshot('research','BTCUSDT',now_ms=200000)
            self.assertEqual(result['rows'][0]['created_at_ms'],123500)
            self.assertEqual(result['authority'],'HISTORICAL_ONLY')
            with connection(self.path) as con: con.execute("UPDATE research_results SET metrics='{\"x\": NaN}'")
            self.assertEqual(sources.snapshot('research','BTCUSDT')['state'],'INVALID_DATA')

    def test_grid_nullable_poc_integer_timestamp_and_not_l2(self):
        with patch.dict(os.environ,{'TERMINAN_GRID_DSN':'synthetic'}), patch.object(sources,'grid_rows',return_value=([dict(t=60000,o=10,h=12,l=9,c=11,buy=3,sell=2,delta=1,trades=4,poc=None)],'pg18-structural-v1')):
            result=sources.snapshot('grid','BTCUSDT',now_ms=120000)
        self.assertIsNone(result['rows'][0]['poc'])
        self.assertIs(type(result['rows'][0]['t']),int)
        self.assertEqual(result['authority'],'AGGREGATED_HISTORY_NOT_L2')


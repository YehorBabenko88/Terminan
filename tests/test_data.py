import os
import sqlite3
import tempfile
import unittest
from terminan import data

class AdapterTests(unittest.TestCase):
    def test_invalid_symbol(self):
        with self.assertRaises(ValueError): data.candles('BTC;DROP')
    def test_missing_sources(self):
        old=os.environ.pop('TERMINAN_STRATTESTER_DB',None)
        try: self.assertEqual(data.instruments(),[])
        finally:
            if old is not None: os.environ['TERMINAN_STRATTESTER_DB']=old
    def test_readonly_candles(self):
        with tempfile.TemporaryDirectory() as d:
            p=os.path.join(d,'market.db');c=sqlite3.connect(p)
            c.execute('CREATE TABLE candles(symbol TEXT,timeframe TEXT,open_time INTEGER,open REAL,high REAL,low REAL,close REAL,volume REAL)')
            c.execute('INSERT INTO candles VALUES(?,?,?,?,?,?,?,?)',('BTCUSDT','1m',123,1,3,1,2,4));c.commit();c.close()
            old=os.environ.get('TERMINAN_STRATTESTER_DB');os.environ['TERMINAN_STRATTESTER_DB']=p
            try:
                self.assertEqual(data.instruments(),['BTCUSDT'])
                self.assertEqual(data.candles('BTCUSDT')[0]['c'],2)
            finally:
                if old is None:os.environ.pop('TERMINAN_STRATTESTER_DB',None)
                else:os.environ['TERMINAN_STRATTESTER_DB']=old
    def test_current_schema_preserves_completion_for_levels(self):
        from unittest.mock import patch
        from terminan.levels import merge_levels
        with tempfile.TemporaryDirectory() as d:
            p=os.path.join(d,'market.db')
            c=sqlite3.connect(p)
            c.execute('CREATE TABLE candles(symbol TEXT,timeframe TEXT,open_time INTEGER,open REAL,high REAL,low REAL,close REAL,volume REAL,complete INTEGER)')
            c.executemany('INSERT INTO candles VALUES(?,?,?,?,?,?,?,?,?)',[
                ('BTCUSDT','1h',0,10,12,8,11,20,1),
                ('BTCUSDT','1h',3600000,11,15,7,13,21,0),
            ])
            c.commit();c.close()
            with patch.dict(os.environ,{'TERMINAN_STRATTESTER_DB':p}):
                rows=data.candles('BTCUSDT','1h')
            self.assertEqual([r['complete'] for r in rows],[True,False])
            self.assertEqual({l['price'] for l in merge_levels({'1h':rows},7200000)},{8,12})
if __name__=='__main__':unittest.main()

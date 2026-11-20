import unittest,tempfile,sqlite3
from pathlib import Path
from contextlib import closing
from terminan.migration.candle_snapshot import read_candle_snapshot,read_instrument_snapshot

class CandleSnapshotTests(unittest.TestCase):
    def test_frozen_source_rows_are_preserved_without_active_database_alias(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'market.sqlite'
            with closing(sqlite3.connect(source)) as db, db:
                db.execute('CREATE TABLE candles(symbol TEXT,timeframe TEXT,open_time INTEGER,open REAL,high REAL,low REAL,close REAL,volume REAL)')
                db.execute('INSERT INTO candles VALUES(?,?,?,?,?,?,?,?)',('BTCUSDT','1m',123,1,3,1,2,4))
            original=source.read_bytes()
            self.assertEqual(read_instrument_snapshot(source),['BTCUSDT'])
            self.assertEqual(read_candle_snapshot(source,'BTCUSDT'),[dict(t=123,o=1.0,h=3.0,l=1.0,c=2.0,v=4.0)])
            self.assertEqual(source.read_bytes(),original)
            self.assertEqual(list(source.parent.glob('market.sqlite*')),[source])

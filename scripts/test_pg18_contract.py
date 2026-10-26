"""CI-only disposable PostgreSQL fixture; never accepts a production DSN."""
import os
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from terminan.g0_sources import snapshot

DSN='postgresql://g0:g0_synthetic_only@127.0.0.1:5432/g0_synthetic'

class PostgreSQL18Contract(unittest.TestCase):
    def test_actual_pinned_grid_ddl_readonly_and_negative_schema(self):
        self.assertEqual(os.environ.get('G0_SYNTHETIC_PG'),'1','Only disposable CI fixture authorized')
        ddl=(Path(os.environ['GRID_REPO'])/'grid/schema.sql').read_text()
        with psycopg.connect(DSN,autocommit=True) as con:
            con.execute(ddl)
            con.execute("INSERT INTO candles_1m VALUES('BTCUSDT',to_timestamp(60),10,12,9,11,3,2,1,4,NULL)")
            con.execute("INSERT INTO footprint_1m VALUES('BTCUSDT',to_timestamp(60),10,3,2,1,5,2,2)")
            con.execute("INSERT INTO nodes(node_id,last_seen) VALUES('synthetic-node',to_timestamp(60))")
        os.environ['TERMINAN_GRID_DSN']=DSN
        try:
            view=snapshot('grid','BTCUSDT',now_ms=120000)
            self.assertEqual(view['state'],'HISTORICAL',view)
            self.assertEqual(view['rows'][0]['t'],60000)
            self.assertIsNone(view['rows'][0]['poc'])
            self.assertEqual(snapshot('footprint','BTCUSDT',now_ms=120000)['rows'][0]['volume'],5)
            self.assertEqual(snapshot('health','BTCUSDT',now_ms=120000)['state'],'FRESH')
            with psycopg.connect(DSN) as con:
                con.read_only=True
                with self.assertRaises(psycopg.errors.ReadOnlySqlTransaction):con.execute('DELETE FROM candles_1m')
            with psycopg.connect(DSN,autocommit=True) as con:
                con.execute('ALTER TABLE candles_1m RENAME COLUMN poc_price TO incompatible_poc')
            self.assertEqual(snapshot('grid','BTCUSDT')['state'],'SCHEMA_MISMATCH')
        finally:os.environ.pop('TERMINAN_GRID_DSN',None)

if __name__=='__main__':unittest.main(verbosity=2)

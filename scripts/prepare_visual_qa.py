"""Create only a new test-owned snapshot and temporary SQLite cache."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from terminan.infrastructure import STAGES
from terminan.saved_cache import open_cache,ALGORITHM
from terminan.cache_queue import init_queue,submit,run_once
root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=False)
snapshot=dict(schema='unified.lifecycle.v1',api_version=dict(major=1,minor=0),producer='unified-system',mode='PLAN_ONLY',epoch='00000000-0000-0000-0000-000000000001',sequence=0,evidence_class='SYNTHETIC',execution_authorized=False,trading_authorized=False,stages=[dict(stage=s,status='NOT_STARTED',completed=0,total=0) for s in STAGES],fleet=dict(nodes=[dict(id=str(i)+'a'*127,state='UNAVAILABLE',cpu=None,memory=None,disk=None) for i in range(7)],links=[]))
(root/'snapshot.json').write_text(json.dumps(snapshot),encoding='utf8')
con=init_queue(open_cache(root/'cache.sqlite'));start=1767225600000
identity=dict(source='grid',source_revision='a'*64,dataset='candles_1m',symbol='BTCUSDT',timeframe='5m',from_ms=start,to_ms=start+240000,algorithm=ALGORITHM,parameters_hash='b'*64)
candles=[dict(symbol='BTCUSDT',ts=start+i*60000,open=100,high=102,low=99,close=101,buy_volume=2,sell_volume=1) for i in range(5)]
source=dict(source_revision='a'*64,candles=candles,footprint=[dict(symbol='BTCUSDT',ts=c['ts'],price=100,buy_volume=2,sell_volume=1) for c in candles])
submit(con,identity,source);assert run_once(con)['state']=='FINISHED';con.close()

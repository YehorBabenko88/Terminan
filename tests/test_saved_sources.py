import copy, hashlib, json, sqlite3, tempfile, unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
from terminan.saved_sources import SavedSources, SourceError, demo_config, CATALOG

class SavedTests(unittest.TestCase):
 def setUp(self): self.sources=SavedSources(demo_config())
 def test_disabled_no_connections(self):
  self.assertEqual(SavedSources().catalog()['sources'],[])
  with self.assertRaises(SourceError): SavedSources().page('grid-demo','candles_1m')
 def test_keyset_pages_and_identity(self):
  a=self.sources.page('grid-demo','candles_1m',limit=2)
  b=self.sources.page('grid-demo','candles_1m',limit=2,cursor=a['next_cursor'])
  self.assertEqual(len(a['rows']),2);self.assertLess(a['rows'][-1]['ts'],b['rows'][0]['ts'])
  self.assertEqual(a['authority'],'SYNTHETIC_ONLY')
  with self.assertRaises(SourceError):self.sources.page('grid-demo','candles_1m',symbol='ETHUSDT',cursor=a['next_cursor'])
  with self.assertRaises(SourceError):self.sources.page('grid-demo','footprint_1m',cursor=a['next_cursor'])
 def test_multi_candle_and_research(self):
  f=self.sources.page('grid-demo','footprint_1m',limit=100)
  self.assertGreater(len(set(r['ts'] for r in f['rows'])),3)
  r=self.sources.page('research-demo','research_results')['rows'][0]
  self.assertIn('net_pnl',r['metrics']);self.assertEqual(r['publication_state'],'PUBLISHED_UNVERIFIED')
 def test_limits_and_unsupported(self):
  for kw in ({'limit':0},{'limit':True},{'limit':201},{'timeframe':'5m'},{'symbol':'btc'},{'cursor':'bad'}):
   with self.subTest(kw=kw),self.assertRaises(SourceError):self.sources.page('grid-demo','candles_1m',**kw)
  with self.assertRaises(SourceError):self.sources.page('grid-demo','ml_jobs')
 def test_sqlite_read_only_schema_and_epoch(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'data.sqlite';c=sqlite3.connect(p)
   c.executescript("CREATE TABLE schema_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);INSERT INTO schema_meta VALUES('schema_version','2');CREATE TABLE candles(symbol TEXT NOT NULL,timeframe TEXT NOT NULL,open_time INTEGER NOT NULL,open REAL NOT NULL,high REAL NOT NULL,low REAL NOT NULL,close REAL NOT NULL,volume REAL NOT NULL,turnover REAL,complete INTEGER NOT NULL DEFAULT 1,PRIMARY KEY(symbol,timeframe,open_time));")
   for i in range(5):c.execute('INSERT INTO candles VALUES(?,?,?,?,?,?,?,?,?,?)',('BTCUSDT','1m',1767225600000+i*60000,10,12,9,11,4,None,1))
   c.commit();c.close();before=hashlib.sha256(p.read_bytes()).hexdigest()
   conf={'version':1,'sources':[{'id':'test','source':'strattester','backend':'sqlite','path':str(p),'source_sha':CATALOG['strattester']['sha'],'schema_id':'market2'}]}
   s=SavedSources(conf);a=s.page('test','candles',limit=2)
   self.assertEqual(a['authority'],'HISTORICAL_ONLY');self.assertEqual(a['rows'][0]['open_time'],1767225600000)
   self.assertEqual(before,hashlib.sha256(p.read_bytes()).hexdigest())
   c=sqlite3.connect(p);c.execute('UPDATE candles SET close=10');c.commit();c.close()
   with self.assertRaises(SourceError):s.page('test','candles',limit=2,cursor=a['next_cursor'])
 def test_invalid_payload_and_pin(self):
  for change in ('nan','future','identity','duplicate','schema'):
   with tempfile.TemporaryDirectory() as t:
    cfg=demo_config();src=cfg['sources'][0];x=json.loads(Path(src['path']).read_text())
    if change=='nan':x['datasets']['candles_1m'][0]['volume']=float('nan')
    if change=='future':x['datasets']['candles_1m'][0]['ts']=9999999999999
    if change=='identity':x['datasets']['candles_1m'][0]['symbol']='BAD'
    if change=='duplicate':x['datasets']['candles_1m'].insert(0,copy.deepcopy(x['datasets']['candles_1m'][0]))
    if change=='schema':x['schema_id']='unknown'
    p=Path(t)/'x.json';p.write_text(json.dumps(x));src['path']=str(p)
    with self.subTest(change=change),self.assertRaises(SourceError):SavedSources(cfg).page('grid-demo','candles_1m')
  cfg=demo_config();cfg['sources'][0]['source_sha']='0'*40
  with self.assertRaises(SourceError):SavedSources(cfg)
 def test_payload_semantics(self):
  for field,value in [('delta',999),('buy_volume',-1),('price',0)]:
   with tempfile.TemporaryDirectory() as t:
    cfg=demo_config();s=cfg['sources'][0];x=json.loads(Path(s['path']).read_text());x['datasets']['footprint_1m'][0][field]=value
    p=Path(t)/'x.json';p.write_text(json.dumps(x));s['path']=str(p)
    with self.subTest(field=field),self.assertRaises(SourceError):SavedSources(cfg).page('grid-demo','footprint_1m')
 def test_sqlite_research_seconds_and_large_cell(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'r.sqlite';c=sqlite3.connect(p);c.execute('CREATE TABLE research_results(run_id TEXT NOT NULL,symbol TEXT NOT NULL,strategy_id TEXT NOT NULL,strategy_version TEXT NOT NULL,created_at REAL NOT NULL,metrics TEXT NOT NULL,job_id TEXT,lease_token INTEGER NOT NULL DEFAULT 0,node_generation INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(run_id,symbol,strategy_id,strategy_version))')
   c.execute('INSERT INTO research_results VALUES(?,?,?,?,?,?,?,?,?)',('one','BTCUSDT','s','1',1767225600.125,json.dumps({'net_pnl':1,'coverage':'COMPLETE_HISTORY'}),None,0,0));c.commit()
   cfg={'version':1,'sources':[dict(id='r',source='strattester',backend='sqlite',path=str(p),source_sha=CATALOG['strattester']['sha'],schema_id='results1')]};s=SavedSources(cfg)
   self.assertEqual(s.page('r','research_results')['rows'][0]['created_at'],1767225600125)
   c.execute('UPDATE research_results SET metrics=?',(json.dumps({'large':'x'*1000000}),));c.commit();c.close()
   with self.assertRaises(SourceError) as e:s.page('r','research_results')
   self.assertEqual(e.exception.code,'RESOURCE_LIMIT')
 def test_shards_require_ready_never_create_or_fallback(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);manifest=p/'manifest.sqlite3';c=sqlite3.connect(manifest);c.execute('CREATE TABLE shard_manifest(symbol TEXT PRIMARY KEY,state TEXT NOT NULL)');c.execute("INSERT INTO shard_manifest VALUES('BTCUSDT','MIGRATING')");c.commit();c.close()
   cfg={'version':1,'sources':[dict(id='shard',source='strattester',backend='sqlite-shards',path=str(p),source_sha=CATALOG['strattester']['sha'],schema_id='market2')]}
   with self.assertRaises(SourceError) as e:SavedSources(cfg).page('shard','candles')
   self.assertEqual(e.exception.code,'SHARD_NOT_READY');self.assertEqual(sorted(x.name for x in p.iterdir()),['manifest.sqlite3'])
 def test_catalog_source_hashes(self):
  for source,folder in [('grid','grid'),('strattester','strattester')]:
   root=Path(__file__).resolve().parents[2]/folder
   if not root.exists():self.fail('Pinned source checkout required')
   for name,expected in CATALOG[source]['files'].items():self.assertEqual(hashlib.sha256((root/name).read_text(encoding='utf8').encode()).hexdigest(),expected)
 def test_postgres_query_plan_readonly_without_server(self):
  spec=CATALOG['grid']['datasets']['candles_1m'];fixture=json.loads(Path(demo_config()['sources'][0]['path']).read_text())['datasets']['candles_1m'][0]
  statements=[];connections=[]
  class Result:
   def __init__(self,rows):self.rows=rows
   def __iter__(self):return iter(self.rows)
   def fetchone(self):return self.rows[0]
   def fetchmany(self,n):return self.rows[:n]
  class Connection:
   info=SimpleNamespace(server_version=180000)
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def execute(self,sql,args=()):
    statements.append((sql,args))
    if 'pg_current_wal_lsn' in sql:return Result([('stable',)])
    if 'schema_migrations' in sql:return Result([(m['version'],m['name']) for m in CATALOG['grid']['migration_history']])
    if 'table_constraints' in sql:return Result([(k,) for k in spec['key']])
    if 'information_schema' in sql:return Result([(k,{'timestamptz':'timestamp with time zone','bigserial':'bigint'}.get(v['type'],v['type'])) for k,v in spec['columns'].items()])
    if sql.startswith('SELECT CASE'):return Result([tuple(fixture[k] for k in spec['projection'])+(False,)])
    return Result([])
  def connect(*args,**kw):connections.append(kw);return Connection()
  conf={'version':1,'sources':[dict(id='pg',source='grid',backend='postgres',dsn_env='TERMINAN_SAVED_TEST',source_sha=CATALOG['grid']['sha'],schema_id='grid46')]}
  with patch.dict('sys.modules',{'psycopg':SimpleNamespace(connect=connect)}),patch.dict('os.environ',{'TERMINAN_SAVED_TEST':'isolated-fake-value'}):
   result=SavedSources(conf).page('pg','candles_1m');self.assertEqual(len(result['rows']),1)
  self.assertTrue(all(sql.startswith(('SELECT','SET TRANSACTION')) for sql,_ in statements))
  self.assertTrue(all('default_transaction_read_only=on' in c['options'] and 'statement_timeout=2000' in c['options'] for c in connections))
 def test_complete_and_gap_states(self):
  with tempfile.TemporaryDirectory() as t:
   cfg=demo_config();src=cfg['sources'][1];x=json.loads(Path(src['path']).read_text());x['datasets']['candles'][0]['complete']=0;p=Path(t)/'x.json';p.write_text(json.dumps(x));src['path']=str(p)
   result=SavedSources(cfg).page('market-demo','candles');self.assertEqual(result['state'],'PARTIAL');self.assertIs(result['coverage']['complete'],False)
 def test_explicit_legacy_candles_profile(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'legacy.sqlite';c=sqlite3.connect(p);c.executescript("CREATE TABLE candles(symbol TEXT NOT NULL,ts INTEGER NOT NULL,open REAL NOT NULL,high REAL NOT NULL,low REAL NOT NULL,close REAL NOT NULL,volume REAL NOT NULL,turnover REAL,PRIMARY KEY(symbol,ts));INSERT INTO candles VALUES('BTCUSDT',1767225600000,1,2,1,2,3,NULL);");c.close()
   cfg={'version':1,'sources':[dict(id='legacy',source='strattester',backend='sqlite',path=str(p),source_sha=CATALOG['strattester']['sha'],schema_id='legacy-candles1')]};s=SavedSources(cfg)
   self.assertEqual(s.page('legacy','legacy_candles')['rows'][0]['ts'],1767225600000)
   with self.assertRaises(SourceError):s.page('legacy','legacy_candles',timeframe='5m')
 def test_missing_primary_key_fails_schema(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'legacy.sqlite';c=sqlite3.connect(p);c.execute('CREATE TABLE candles(symbol TEXT NOT NULL,ts INTEGER NOT NULL,open REAL NOT NULL,high REAL NOT NULL,low REAL NOT NULL,close REAL NOT NULL,volume REAL NOT NULL,turnover REAL)');c.close()
   cfg={'version':1,'sources':[dict(id='legacy',source='strattester',backend='sqlite',path=str(p),source_sha=CATALOG['strattester']['sha'],schema_id='legacy-candles1')]}
   with self.assertRaises(SourceError) as e:SavedSources(cfg).page('legacy','legacy_candles')
   self.assertEqual(e.exception.code,'SCHEMA_MISMATCH')
 def test_premium_index_can_be_negative(self):
  with tempfile.TemporaryDirectory() as t:
   cfg=demo_config();src=cfg['sources'][1];x=json.loads(Path(src['path']).read_text());x['datasets']['premium_index'][0].update(open=-.001,high=.001,low=-.002,close=0);p=Path(t)/'x.json';p.write_text(json.dumps(x));src['path']=str(p)
   self.assertEqual(SavedSources(cfg).page('market-demo','premium_index')['rows'][0]['close'],0)
 def test_utc_window_and_cursor_binding(self):
  start=1767225600000+600000
  p=self.sources.page('grid-demo','candles_1m',from_ms=start,limit=2)
  self.assertEqual(p['rows'][0]['ts'],start)
  with self.assertRaises(SourceError):self.sources.page('grid-demo','candles_1m',from_ms=start+60000,limit=2,cursor=p['next_cursor'])
  with self.assertRaises(SourceError):self.sources.page('grid-demo','candles_1m',from_ms=1767230000000,cutoff_ms=1767225600000)
 def test_scheduled_deadline_is_not_future_observation(self):
  with tempfile.TemporaryDirectory() as t:
   cfg=demo_config();src=cfg['sources'][0];x=json.loads(Path(src['path']).read_text());asof=x['as_of_ms']
   x['datasets']['scientific_negative_memory']=[dict(fingerprint='one',reason='negative evidence',evidence_count=1,cooldown_until=asof+60000,details={},updated_at=asof)]
   p=Path(t)/'x.json';p.write_text(json.dumps(x));src['path']=str(p)
   self.assertGreater(SavedSources(cfg).page('grid-demo','scientific_negative_memory')['rows'][0]['cooldown_until'],asof)
   x['datasets']['scientific_negative_memory'][0]['updated_at']=asof+1;p.write_text(json.dumps(x))
   with self.assertRaises(SourceError):SavedSources(cfg).page('grid-demo','scientific_negative_memory')

import ast,re,json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1];g=root.parent/'grid';s=root.parent/'strattester'
def h(p):return hashlib.sha256(p.read_text(encoding='utf8').encode()).hexdigest()
def parse(sql):
 out={}
 for m in re.finditer(r'CREATE TABLE IF NOT EXISTS (\w+)\s*\(',sql,re.I):
  start=m.end();depth=1;i=start
  while i<len(sql) and depth:
   if sql[i]=='(':depth+=1
   if sql[i]==')':depth-=1
   i+=1
  body=sql[start:i-1];parts=[];level=0;last=0
  for n,ch in enumerate(body):
   if ch=='(':level+=1
   if ch==')':level-=1
   if ch==',' and level==0:parts.append(body[last:n].strip());last=n+1
  parts.append(body[last:].strip());cols={};keys=[]
  for part in parts:
   pk=re.match(r'PRIMARY KEY\s*\(([^)]+)\)',part,re.I)
   if pk:keys=[x.strip() for x in pk[1].split(',')];continue
   cm=re.match(r'(\w+)\s+(double precision|character varying|\w+(?:\[\])?)',part,re.I)
   if cm and cm[1].lower() not in ('constraint','unique','check','foreign'):
    cols[cm[1]]={'type':cm[2].lower(),'nullable':'NOT NULL' not in part.upper() and 'PRIMARY KEY' not in part.upper()}
    if 'PRIMARY KEY' in part.upper():keys=[cm[1]]
  out[m[1]]={'columns':cols,'key':keys}
 for m in re.finditer(r'ALTER TABLE (\w+) ADD COLUMN (?:IF NOT EXISTS )?(\w+)\s+(double precision|\w+)([^\n]*)',sql,re.I):
  if m[1] in out:out[m[1]]['columns'][m[2]]={'type':m[3].lower(),'nullable':'NOT NULL' not in m[4].upper()}
 return out
mod=ast.parse((g/'grid/migrations.py').read_text());migrations=next(ast.literal_eval(n.value) for n in mod.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MIGRATIONS' for t in n.targets))
gsql=(g/'grid/schema.sql').read_text()+'\n'+'\n'.join(q for _,_,queries in migrations for q in queries)
dbfiles={}
for file in sorted((g/'grid').glob('*.py')):
 if file.name=='migrations.py':continue
 try:tree=ast.parse(file.read_text(encoding='utf8'))
 except (SyntaxError,UnicodeError):continue
 strings=[n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'CREATE TABLE' in n.value]
 if strings:dbfiles['grid/'+file.name]=h(file);gsql+='\n'+'\n'.join(strings)
gtables=parse(gsql)
market=ast.parse((s/'strattester/marketdata/schema.py').read_text());msql=next(ast.literal_eval(n.value) for n in market.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SCHEMA_SQL' for t in n.targets))
rsql='\n'.join(n.value for n in ast.walk(ast.parse((s/'strattester/persistence/result_store.py').read_text())) if isinstance(n,ast.Constant) and isinstance(n.value,str) and ('CREATE TABLE' in n.value or 'ALTER TABLE' in n.value))
# Explicit safe fields only: no operational payload/path/error/host/auth/lease material.
excluded={'extra','storage_uri','payload','error','last_error','hostname','state','metadata','meta','assigned_symbols','book','walls'}
for tables in (gtables,parse(msql),parse(rsql)):
 pass
catalog={}
for source,tables,sha,files in [('grid',gtables,'d537d525296ef34f727996e240ae6c60102c6082',{**dbfiles,'grid/schema.sql':h(g/'grid/schema.sql'),'grid/migrations.py':h(g/'grid/migrations.py'),'grid/terminan_gateway.py':h(g/'grid/terminan_gateway.py')}),('strattester',{**parse(msql),**parse(rsql)},'37ff7e9d12a4d2dccd788fc493c28557dbe8bcea',{'strattester/marketdata/schema.py':h(s/'strattester/marketdata/schema.py'),'strattester/persistence/result_store.py':h(s/'strattester/persistence/result_store.py'),'strattester/research/result_persistence.py':h(s/'strattester/research/result_persistence.py'),'strattester/marketdata/sqlite_store.py':h(s/'strattester/marketdata/sqlite_store.py'),'strattester/marketdata/sharded_store.py':h(s/'strattester/marketdata/sharded_store.py'),'strattester/marketdata/shard_manifest.py':h(s/'strattester/marketdata/shard_manifest.py')})]:
 for name,d in tables.items():
  global_research={'strategy_comparison_results','historical_experiment_runs','scientific_simulation_runs','scientific_hypotheses','scientific_negative_memory','scientific_mining_runs','scientific_methods','historical_scientific_bundles','model_evaluations','model_registry','dataset_snapshots'}
  internal={'observer_checkpoints','consumer_watermarks','retention_holds','market_backfill_state','trade_archive_backfill','trade_archive_discovery','derived_minute_state','scientific_outcome_clock','historical_experiment_checkpoints'}
  d['scope']='SYMBOL' if 'symbol' in d['columns'] else 'GLOBAL'
  d['supported']=bool(d['key'] and ('symbol' in d['columns'] or name in global_research) and name not in internal and not name.startswith('staged_'))
  d['reason']=None if d['supported'] else 'INTERNAL_STATE_OR_NO_STABLE_SYMBOL_KEY'
  d['projection']=[k for k in d['columns'] if k not in excluded and not any(x in k for x in ('lease_','password','secret','dsn','token'))]
  if not set(d['key'])<=set(d['projection']):d['supported']=False;d['reason']='SENSITIVE_KEY'
  d['time_column']=next((k for k in ('ts','open_time','event_ts','event_ts_ms','source_ts','source_start','feature_ts','created_at','updated_at','funding_time','first_seen') if k in d['columns']),None)
  d['schema_id']='grid46' if source=='grid' else 'results1' if 'research_results' in name else 'market2'
  d['native_timeframe']='1m' if name.endswith('_1m') else None
 catalog[source]={'sha':sha,'files':files,'datasets':tables}
catalog['grid']['migration_history']=[{'version':v,'name':n} for v,n,_ in migrations]
legacy=json.loads(json.dumps(catalog['strattester']['datasets']['candles']))
legacy['columns'].pop('timeframe');legacy['columns'].pop('complete');legacy['columns']['ts']=legacy['columns'].pop('open_time')
legacy.update(key=['symbol','ts'],projection=list(legacy['columns']),schema_id='legacy-candles1',time_column='ts',native_timeframe='1m',table='candles')
catalog['strattester']['datasets']['legacy_candles']=legacy
(root/'terminan/fixtures/saved-catalog-v1.json').write_text(json.dumps(catalog,indent=2)+'\n')
for source,c in catalog.items():print(source,len(c['datasets']),'supported',sum(d['supported'] for d in c['datasets'].values()))

"""Actual Data9c declared fixtures; independent hashes and no Data runtime import."""
import copy,json,hashlib,pathlib,unittest
from decimal import localcontext
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parent

def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def fixture():
 f=json.loads((ROOT/'fixtures/history_v12/data9c-delayed-middle.json').read_text());f['independent_pin']='72ef236cd126cfb52b17c8984293e7ed70455b92fade8c29138880adcab168b5';return f
def levels_fixture():
 f=json.loads((ROOT/'fixtures/history_v12/data9c-levels.json').read_text())
 for key,pin in {'window1h':'25d04aa45d932dd5004ec88dba9dfeada73fcf9569afc284e632113fd951e79a','series1h':'5d84ca21e83ac0dab4b5bee671ff7a17f512e41cd623252f1e4014f253a30691','window15m':'d8f783755f97506fb71e8f6911a5a54e55c98f957a214ecffd406b87775e2b4c'}.items():f[key]['independent_pin']=pin
 return f
def analyze(f,decision):
 from terminan.analytics.market_history import analyze_market_history_v12
 return analyze_market_history_v12(f['minute_envelope'],decision_ms=decision,expected_snapshot_id=f['selection']['snapshot_id'],catalog=f['catalog'])
def validate(f,**options):
 from terminan.history_protocol import validate_rollup_v12
 return validate_rollup_v12(f['rollup'],trusted_fingerprint=options.pop('trusted_pin',f['independent_pin']),selection=f['selection'],catalog=f['catalog'],as_of_ms=f['rollup']['as_of_ms'],options=options)
def series(f,decision=7200000,**options):
 from terminan.levels import levels_from_market_data_series_v12
 return levels_from_market_data_series_v12(f['rollup'],trusted_fingerprint=options.pop('trusted_pin',f['independent_pin']),selection=f['selection'],catalog=f['catalog'],decision_ms=decision,**options)
def reseal(p):p['dataset_fingerprint']=digest({k:v for k,v in p.items() if k!='dataset_fingerprint'})
def content(p):
 q=p['request'];return dict(schema='market_data.dataset.v1.2',source=p['source'],identity={k:q[k] for k in ('venue','market_type','symbol','units')},timeframe='1m',representation='historical_aggregate',evidence_class=p['evidence_class'],rows=p['rows'],source_receipts=p['source_receipts'],**{k:p[k] for k in ('turnover_basis','availability_basis','financial_encoding','source_authentication')})
class HistoryV12Tests(unittest.TestCase):
 def test_actual_delayed_middle_analysis_retains_turnover_and_hash_seal(self):
  f=fixture();before=copy.deepcopy(f);x=analyze(f,900000)
  self.assertEqual([r['turnover'] for r in x['rows']],[200,201,202,203,204]);self.assertEqual([r['turnover'] for r in x['candles']],['200.0','201.0','202.0','203.0','204.0'])
  self.assertEqual(x['schema'],'terminan.market.history.analysis.v1.2');self.assertEqual(x['units'],{'price':'USDT/BTC','volume':'BTC','turnover':'USDT'});self.assertEqual(x['point_in_time_availability'],'DECLARED_UNVERIFIED');self.assertFalse(x['h_b_eligible']);self.assertFalse(x['execution_authority']);self.assertEqual(x['analysis_fingerprint'],digest({k:v for k,v in x.items() if k!='analysis_fingerprint'}));self.assertEqual(f,before)
 def test_delayed_middle_prefix_gap_suppresses_levels_until_900000(self):
  f=fixture()
  for decision in (300000,899999):
   x=analyze(f,decision);self.assertEqual(len(x['rows']),4);self.assertEqual(x['coverage_status'],'GAP');self.assertEqual(x['levels'],[])
  self.assertEqual(len(analyze(f,900000)['rows']),5)
 def test_old_analysis_all_three_byte_goldens_unchanged(self):
  from terminan.analytics.market_history import analyze_market_history
  p=json.loads((ROOT/'fixtures/market_history/synthetic-v11.json').read_text())
  for decision,expected in ((60000,'8a2dc6a0da4682832d4fb8cb93d65f0ed7d4dc1e8a2de39c631d511fcb5cf045'),(120000,'8b62d6ec79af7297c7e0126a7b0a3524c1aff4a1c6054086e22c3f0f80c31f06'),(180000,'023219e164a1fcd8040399c2588c396e09be6377f5aa3391204e1bb00e8cfb4c')):
   self.assertEqual(digest(analyze_market_history(p,decision_ms=decision)),expected)
 def test_versions_are_closed_without_turnover_downgrade(self):
  from terminan.analytics.market_history import analyze_market_history,analyze_market_history_v12
  f=fixture()
  with self.assertRaises(ValueError):analyze_market_history(f['minute_envelope'],decision_ms=900000)
  old=json.loads((ROOT/'fixtures/market_history/synthetic-v11.json').read_text())
  with self.assertRaises(ValueError):analyze_market_history_v12(old,decision_ms=180000,expected_snapshot_id=f['selection']['snapshot_id'],catalog=f['catalog'])
 def test_independent_snapshot_pin_and_both_dataset_pairs_mandatory(self):
  from terminan.analytics.market_history import analyze_market_history_v12
  f=fixture()
  for pin in (None,'f'*64):
   with self.assertRaises(ValueError):analyze_market_history_v12(f['minute_envelope'],decision_ms=900000,expected_snapshot_id=pin,catalog=f['catalog'])
  f['minute_envelope']['rows'][-1]['turnover']=999;f['minute_envelope']['dataset_id']=digest(content(f['minute_envelope']));reseal(f['minute_envelope'])
  with self.assertRaises(ValueError):analyze(f,900000)
 def test_request_source_units_and_all_fixed_declarations_are_bound(self):
  for target,key,value in (('request','schema','old'),('request','symbol','ETHUSDT'),('source','epoch','changed'),('envelope','turnover_basis','VWAP'),('envelope','availability_basis','END_TIME'),('envelope','financial_encoding','DECIMAL_STRING'),('envelope','execution_authority',True)):
   f=fixture();p=f['minute_envelope'];(p if target=='envelope' else p[target])[key]=value;reseal(p)
   with self.assertRaises(ValueError):analyze(f,900000)
 def test_future_invalid_financial_domain_rejects_even_when_fully_resealed(self):
  for value in (-1,0,True,None,float('inf'),2**53+1):
   f=fixture();p=f['minute_envelope'];p['rows'][2]['turnover']=value
   if value!=float('inf'):p['dataset_id']=digest(content(p));reseal(p)
   with self.assertRaises(ValueError):analyze(f,60000)
 def test_receipt_roster_versions_pins_and_clocks_reject_before_projection(self):
  for which in ('schema','pin','extra','missing','watermark'):
   f=fixture();entry=next(iter(f['catalog'].values()));t=entry['trust'];fp=entry['revisions'][0]
   if which=='schema':t['receipts'][fp]['schema']='old'
   elif which=='pin':t['receipt_pins'][fp]='f'*64
   elif which=='extra':t['receipts']['f'*64]=t['receipts'][fp]
   elif which=='missing':entry['revisions'].pop()
   else:t['receipts'][fp]['watermark_ms']=900001
   pin=digest(entry);f['catalog']={pin:entry};f['selection']['snapshot_id']=pin
   with self.assertRaises(ValueError):analyze(f,900000)
 def test_strict_14_fields_and_actual_availability_clock(self):
  for key,value in (('available_at_ms',179999),('watermark_ms',900001),('event_end_ms',True),('source_receipt_hash','f'*64)):
   f=fixture();p=f['minute_envelope'];p['rows'][2][key]=value;p['dataset_id']=digest(content(p));reseal(p)
   with self.assertRaises(ValueError):analyze(f,900000)
  f=fixture();f['minute_envelope']['rows'][0]['extra']=1
  with self.assertRaises(ValueError):analyze(f,900000)
 def test_foreign_selected_unused_and_nested_keys_have_zero_callbacks(self):
  calls=[]
  class Foreign(str):
   __hash__=str.__hash__
   def __eq__(self,other):calls.append('EQ');return str.__eq__(self,other)
  for where in ('selected','unused','payload','request','units','receipt'):
   f=fixture();pin=f['selection']['snapshot_id'];entry=f['catalog'][pin]
   if where=='selected':f['catalog']={Foreign(pin):entry}
   elif where=='unused':f['catalog'][Foreign('unused')]=entry
   else:
    target={'payload':f['minute_envelope'],'request':entry['request'],'units':entry['request']['units'],'receipt':next(iter(entry['trust']['receipts'].values()))}[where]
    key=next(iter(target));value=target.pop(key);target[Foreign(key)]=value
   calls.clear()
   with self.assertRaises(ValueError):analyze(f,900000)
   self.assertEqual(calls,[])
 def test_joint_detach_survives_math_callback_clearing_original_maps(self):
  import market_math
  f=fixture();expected=analyze(f,900000);original=market_math.lossless_nonnegative_binary64_valid
  def mutate(value):
   f['catalog'].clear();f['minute_envelope'].clear();f['selection'].clear();return original(value)
  with patch.object(market_math,'lossless_nonnegative_binary64_valid',side_effect=mutate):actual=analyze(f,900000)
  self.assertEqual(actual,expected)
 def test_graph_budgets_and_foreign_metaclass_refuse_before_math(self):
  class Meta(type):
   def __eq__(cls,other):raise AssertionError('META_CALLBACK')
  class Foreign(metaclass=Meta):pass
  f=fixture();f['catalog']['unused']=Foreign()
  with patch('market_math.lossless_nonnegative_binary64_valid',side_effect=AssertionError('MATH_CALLED')):
   with self.assertRaises(ValueError):analyze(f,900000)
  f=fixture();f['catalog']['unused']='x'*(8*1024*1024+1)
  with self.assertRaises(ValueError):analyze(f,900000)
 def test_hostile_decimal_context_does_not_change_analysis_or_flags(self):
  f=fixture();expected=analyze(f,900000)
  with localcontext() as ctx:
   ctx.prec=1
   for key in ctx.traps:ctx.traps[key]=True
   flags=dict(ctx.flags);actual=analyze(f,900000);self.assertEqual(dict(ctx.flags),flags)
  self.assertEqual(actual,expected)
 def test_actual_5m_rollup_protocol_keeps_1010_available900000(self):
  f=fixture();f['selection']=dict(f['selection'],operation='window',timeframe='5m');p,_=validate(f)
  self.assertEqual((p['rows'][0]['turnover'],p['rows'][0]['available_at_ms']),(1010,900000));self.assertEqual(len(p['rows'][0]),10)
 def test_5m_15m_valid_protocol_cannot_be_mapped_into_math_levels(self):
  from terminan.levels import market_data_level_candles_v12
  f=fixture();f['selection']=dict(f['selection'],operation='window',timeframe='5m')
  with self.assertRaises(ValueError):market_data_level_candles_v12(f['rollup'],trusted_fingerprint=f['independent_pin'],selection=f['selection'],catalog=f['catalog'],as_of_ms=900000)
  f=levels_fixture()['window15m'];p,_=validate(f);self.assertEqual(p['rows'][0]['turnover'],3105)
  with self.assertRaises(ValueError):market_data_level_candles_v12(f['rollup'],trusted_fingerprint=f['independent_pin'],selection=f['selection'],catalog=f['catalog'],as_of_ms=900000)
 def test_actual_one_hour_candle_projects_after_financial_preflight(self):
  from terminan.levels import market_data_level_candles_v12
  f=levels_fixture()['window1h'];x=market_data_level_candles_v12(f['rollup'],trusted_fingerprint=f['independent_pin'],selection=f['selection'],catalog=f['catalog'],as_of_ms=7200000)
  self.assertEqual(x,[{'t':0,'h':259.0,'l':200.0,'complete':True}])
 def test_cross_page_actual_series_uses_existing_math_kernel(self):
  from terminan.levels import untouched_levels
  f=levels_fixture()['series1h'];x=series(f)
  expected=untouched_levels([dict(t=0,h=259.0,l=200.0,complete=True),dict(t=3600000,h=259.0,l=200.0,complete=True)],'1h',7200000)
  self.assertEqual(x,expected)
 def test_series_independent_fingerprint_parent_order_and_range_pins(self):
  f=levels_fixture()['series1h']
  from terminan.levels import levels_from_market_data_series_v12
  with self.assertRaises(ValueError):levels_from_market_data_series_v12(f['rollup'],trusted_fingerprint='f'*64,selection=f['selection'],catalog=f['catalog'],decision_ms=7200000)
  for mutation in (lambda p:p['parents'].reverse(),lambda p:p['selection']['snapshot_ids'].reverse(),lambda p:p['parents'][0].update(dataset_id='f'*64),lambda p:p['rows'].reverse(),lambda p:p['selection'].update(start_ms=60000)):
   f=levels_fixture()['series1h'];mutation(f['rollup']);reseal(f['rollup'])
   with self.assertRaises(ValueError):series(f,trusted_pin=digest({k:v for k,v in f['rollup'].items() if k!='dataset_fingerprint'}))
 def test_series_future_invalid_turnover_refuses_before_high_low_projection(self):
  for value in (-1,0,True,None,2**53+1):
   f=levels_fixture()['series1h'];f['rollup']['rows'][-1]['turnover']=value;reseal(f['rollup'])
   with patch('terminan.levels.untouched_levels',side_effect=AssertionError('PROJECTED')):
    with self.assertRaises(ValueError):series(f,decision=3600000,trusted_pin=digest({k:v for k,v in f['rollup'].items() if k!='dataset_fingerprint'}))
 def test_series_options_types_clocks_and_refusals_are_jointly_admitted(self):
  for decision,opts in ((True,{}),(7200001,{}),(7200000,{'tick_size':True}),(7200000,{'tick_size':-1}),(7200000,{'max_levels':True}),(7200000,{'max_levels':0})):
   with self.assertRaises(ValueError):series(levels_fixture()['series1h'],decision=decision,**opts)
 def test_rollup_cannot_hide_extra_fields_units_basis_or_authority(self):
  for key,value in (('extra',1),('execution_authority',True),('turnover_basis','VWAP'),('units',{'price':'USDT/BTC','volume':'BTC'}),('source_authentication','VERIFIED')):
   f=levels_fixture()['series1h'];f['rollup'][key]=value;reseal(f['rollup'])
   with self.assertRaises(ValueError):series(f,trusted_pin=digest({k:v for k,v in f['rollup'].items() if k!='dataset_fingerprint'}))
 def test_math_owner_refusals_abort_without_result(self):
  with patch('market_math.candle_ohlcv_turnover_valid',side_effect=ValueError('MATH_REFUSED')):
   with self.assertRaisesRegex(ValueError,'MATH_REFUSED'):analyze(fixture(),900000)
 def test_no_data_runtime_import_is_required_by_term_boundary(self):
  import builtins
  original=builtins.__import__
  def no_data(name,*a,**k):
   if name=='market_data' or name.startswith('market_data.'):raise AssertionError('DATA_RUNTIME_IMPORT')
   return original(name,*a,**k)
  with patch.object(builtins,'__import__',side_effect=no_data):analyze(fixture(),900000);series(levels_fixture()['series1h'])

 def test_fully_resealed_future_financial_domain_with_rebound_catalog_still_refuses(self):
  for key,value in (('turnover',-1),('turnover',0),('turnover',True),('volume',2**53+1),('open',0),('high',1)):
   f=fixture();p=f['minute_envelope'];p['rows'][-1][key]=value;p['dataset_id']=digest(content(p));reseal(p)
   entry=next(iter(f['catalog'].values()));entry['dataset_id']=p['dataset_id'];entry['dataset_fingerprint']=p['dataset_fingerprint'];pin=digest(entry);f['catalog']={pin:entry};f['selection']['snapshot_id']=pin
   with patch('terminan.analytics.market_history.untouched_levels',side_effect=AssertionError('PROJECTED')):
    with self.assertRaises(ValueError):analyze(f,60000)
 def test_all_parent_receipt_availability_max_is_checked_before_projection(self):
  f=fixture();f['selection']=dict(f['selection'],operation='window',timeframe='5m');f['rollup']['rows'][0]['available_at_ms']=300000;reseal(f['rollup'])
  with self.assertRaisesRegex(ValueError,'ALL_PARENT_AVAILABILITY'):validate(f,trusted_pin=digest({k:v for k,v in f['rollup'].items() if k!='dataset_fingerprint'}))
 def test_rollup_all_future_financial_fields_are_checked_even_with_new_full_pin(self):
  for key,value in (('volume',0),('open',0),('high',1),('turnover',2**53+1),('turnover',True)):
   f=levels_fixture()['series1h'];f['rollup']['rows'][-1][key]=value;reseal(f['rollup'])
   with patch('terminan.levels.untouched_levels',side_effect=AssertionError('PROJECTED')):
    with self.assertRaises(ValueError):series(f,decision=3600000,trusted_pin=digest({k:v for k,v in f['rollup'].items() if k!='dataset_fingerprint'}))
 def test_rollup_joint_copy_rejects_foreign_pin_selection_options_and_unused_catalog(self):
  from terminan.history_protocol import validate_rollup_v12
  calls=[]
  class Foreign(str):
   __hash__=str.__hash__
   def __eq__(self,other):calls.append('EQ');return str.__eq__(self,other)
  for where in ('pin','selection','options','catalog','row'):
   f=levels_fixture()['series1h'];pin=f['rollup']['dataset_fingerprint'];options={}
   if where=='pin':pin=Foreign(pin)
   elif where=='selection':value=f['selection'].pop('schema');f['selection'][Foreign('schema')]=value
   elif where=='options':options={Foreign('decision_ms'):7200000,'tick_size':0,'max_levels':200}
   elif where=='catalog':f['catalog'][Foreign('unused')]=None
   else:value=f['rollup']['rows'][0].pop('turnover');f['rollup']['rows'][0][Foreign('turnover')]=value
   calls.clear()
   with patch('market_math.lossless_nonnegative_binary64_valid',side_effect=AssertionError('MATH_CALLED')):
    with self.assertRaises(ValueError):validate_rollup_v12(f['rollup'],trusted_fingerprint=pin,selection=f['selection'],catalog=f['catalog'],as_of_ms=7200000,options=options)
   self.assertEqual(calls,[])
 def test_series_joint_copy_survives_math_callback_clearing_all_originals(self):
  import market_math
  f=levels_fixture()['series1h'];expected=series(f);original=market_math.lossless_nonnegative_binary64_valid
  def mutate(value):
   f['rollup'].clear();f['selection'].clear();f['catalog'].clear();return original(value)
  with patch.object(market_math,'lossless_nonnegative_binary64_valid',side_effect=mutate):actual=series(f)
  self.assertEqual(actual,expected)
 def test_series_known_prefix_uses_actual_delayed_availability_and_suppresses_gap(self):
  f=levels_fixture()['series1h'];firstpin=f['selection']['snapshot_ids'][0];entry=f['catalog'].pop(firstpin);fp=entry['revisions'][30]
  a=entry['trust']['receipts'][fp];a['available_at_ms']=7200000;entry['trust']['receipt_pins'][fp]=digest(a);newpin=digest(entry);f['catalog'][newpin]=entry;f['selection']['snapshot_ids'][0]=newpin
  f['rollup']['selection']['snapshot_ids'][0]=newpin;f['rollup']['parents'][0]['snapshot_id']=newpin;f['rollup']['rows'][0]['available_at_ms']=7200000;reseal(f['rollup'])
  pin=digest({k:v for k,v in f['rollup'].items() if k!='dataset_fingerprint'})
  self.assertEqual(series(f,decision=3600000,trusted_pin=pin),[])
  self.assertTrue(series(f,decision=7200000,trusted_pin=pin))
 def test_wrong_cross_page_source_units_asof_reject_even_with_resealed_entry_pin(self):
  for part,key,value in (('request','as_of_ms',7200001),('request','units',{'price':'USD/BTC','volume':'BTC','turnover':'USD'}),('trust','epoch','other')):
   f=levels_fixture()['series1h'];old=f['selection']['snapshot_ids'][1];entry=f['catalog'].pop(old);entry[part][key]=value;pin=digest(entry);f['catalog'][pin]=entry;f['selection']['snapshot_ids'][1]=pin;f['rollup']['selection']['snapshot_ids'][1]=pin;f['rollup']['parents'][1]['snapshot_id']=pin;reseal(f['rollup'])
   with self.assertRaises(ValueError):series(f,trusted_pin=digest({k:v for k,v in f['rollup'].items() if k!='dataset_fingerprint'}))
 def test_zero_volume_zero_turnover_identity_is_valid_and_never_fabricated(self):
  f=fixture();p=f['minute_envelope'];p['rows'][0]['volume']=0;p['rows'][0]['turnover']=0;p['dataset_id']=digest(content(p));reseal(p);entry=next(iter(f['catalog'].values()));entry['dataset_id']=p['dataset_id'];entry['dataset_fingerprint']=p['dataset_fingerprint'];pin=digest(entry);f['catalog']={pin:entry};f['selection']['snapshot_id']=pin
  self.assertEqual(analyze(f,900000)['rows'][0]['turnover'],0)
  p['rows'][0].pop('turnover')
  with self.assertRaises(ValueError):analyze(f,900000)
 def test_binary64_dto_small_nonzero_amount_preserves_caller_context(self):
  f=fixture();p=f['minute_envelope'];p['rows'][0]['turnover']=5e-324;p['dataset_id']=digest(content(p));reseal(p);entry=next(iter(f['catalog'].values()));entry['dataset_id']=p['dataset_id'];entry['dataset_fingerprint']=p['dataset_fingerprint'];pin=digest(entry);f['catalog']={pin:entry};f['selection']['snapshot_id']=pin
  with localcontext() as ctx:
   ctx.prec=1
   for signal in ctx.traps:ctx.traps[signal]=True
   flags=dict(ctx.flags);x=analyze(f,900000);self.assertEqual(dict(ctx.flags),flags)
  self.assertEqual(x['rows'][0]['turnover'],5e-324)

 def test_actual_multipin_one_candle_operation_is_explicit(self):
  from terminan.levels import market_data_level_candles_v12
  f=json.loads((ROOT/'fixtures/history_v12/data9c-multipin.json').read_text())
  x=market_data_level_candles_v12(f['rollup'],trusted_fingerprint='ef3643bfb9b1fd0cca247898f61f171cba0e00b1abeb3c8d1f5272640549ec47',selection=f['selection'],catalog=f['catalog'],as_of_ms=7200000)
  self.assertEqual(x,[{'t':0,'h':259.0,'l':200.0,'complete':True}]);self.assertEqual(f['rollup']['rows'][0]['turnover'],13770)

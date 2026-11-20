import json,os,unittest
from unittest.mock import patch
from terminan import data
KEY='UNIFIED_MARKET_DATA_READ_CAPABILITY'
class Admission:
 def __init__(self):self.current=True
 def require_current(self):return self.current
 def source_identity(self,module):
  if module!='market_data':raise ValueError('wrong source')
  return {'commit':'a'*40}
class PrivateClientTests(unittest.TestCase):
 def setUp(self):
  self.admission=Admission();self.cap=dict(port=29001,token='b'*64,source_commit='a'*40,release_id='r',epoch='c'*32)
  self.addCleanup(setattr,data,'_private_market_data_client',None)
 def configure(self,cap=None):
  with patch.dict(os.environ,{'UNIFIED_MODULE_ID':'terminan','UNIFIED_RELEASE_ID':'r',KEY:json.dumps(self.cap if cap is None else cap)},clear=True):
   data.configure_market_data_client(self.admission)
   self.assertNotIn(KEY,os.environ)
  return data._private_market_data_client
 def test_scope_and_private_bearer_are_bound_without_public_port_override(self):
  client=self.configure();self.assertNotIn(self.cap['token'],repr(client))
  with patch.object(data,'_market_data_http_get',return_value={'safe':True}) as transport,patch.dict(os.environ,{'MARKET_DATA_API_PORT':'65500'}):
   self.assertEqual(client.get('/internal/v1/capabilities'),{'safe':True})
  self.assertEqual(transport.call_args.args,(29001,'/internal/v1/capabilities'))
  self.assertEqual(transport.call_args.kwargs['headers']['Authorization'],'Bearer '+self.cap['token'])
 def test_invalid_source_release_port_shape_and_missing_admission_refused(self):
  for changes in ({'port':True},{'port':65536},{'source_commit':'d'*40},{'release_id':'other'},{'token':'short'},{'epoch':'arbitrary'},{'extra':'bad'}):
   with self.subTest(changes=changes),self.assertRaises(ValueError):self.configure({**self.cap,**changes})
  with patch.dict(os.environ,{'UNIFIED_MODULE_ID':'terminan','UNIFIED_RELEASE_ID':'r',KEY:json.dumps(self.cap)},clear=True),self.assertRaises(ValueError):data.configure_market_data_client(None)
 def test_only_fixed_read_routes_and_live_admission_can_reach_transport(self):
  client=self.configure()
  with patch.object(data,'_market_data_http_get') as transport:
   for route in ('http://other/internal/v1/health','/v1/candles','/internal/v1/candles?symbol=BTCUSDT&limit=1&extra=1','/internal/v1/health?token=x','/capture','/internal/v1/candles?symbol=BTCUSDT&limit=1001'):
    with self.subTest(route=route),self.assertRaises(ValueError):client.get(route)
   self.admission.current=False
   with self.assertRaises(ValueError):client.get('/internal/v1/health')
   transport.assert_not_called()
 def test_data_restart_old_capability_is_unavailable_without_sql_fallback(self):
  client=self.configure();self.admission.current=True
  with patch.object(data,'_market_data_http_get',side_effect=ValueError('401')),patch.object(data,'sqlite_ro',side_effect=AssertionError('NO_SQL_FALLBACK')):
   self.assertEqual(data.market_data_source_status()['connection'],'UNAVAILABLE')
   self.assertEqual(data.candles('BTCUSDT'),[])
  refreshed={**self.cap,'token':'e'*64,'epoch':'f'*32};new=self.configure(refreshed)
  with patch.object(data,'_market_data_http_get',return_value={}) as transport:new.get('/internal/v1/health')
  self.assertEqual(transport.call_args.kwargs['headers']['Authorization'],'Bearer '+refreshed['token'])
  self.assertIsNot(new,client)
 def test_revocation_during_transport_discards_response(self):
  client=self.configure()
  def revoke(*_,**__):self.admission.current=False;return {'private':'discard'}
  with patch.object(data,'_market_data_http_get',side_effect=revoke),self.assertRaises(ValueError):client.get('/internal/v1/capabilities')
 def test_unmanaged_offline_mode_requires_no_capability(self):
  with patch.dict(os.environ,{},clear=True):data.configure_market_data_client(None)
  self.assertIsNone(data._private_market_data_client)
  with patch.dict(os.environ,{},clear=True),patch.object(data,'_market_data_http_get',side_effect=AssertionError('NO_NETWORK')):
   self.assertEqual(data.market_data_source_status()['connection'],'UNAVAILABLE')

class PrivateStartupTests(unittest.TestCase):
 def test_managed_main_consumes_private_context_before_listener_and_clears_on_exit(self):
  from terminan import server
  cap=dict(port=29001,token='b'*64,source_commit='a'*40,release_id='r',epoch='c'*32)
  with patch.dict(os.environ,{'UNIFIED_MODULE_ID':'terminan','UNIFIED_RELEASE_ID':'r',KEY:json.dumps(cap)},clear=True),patch.object(server,'ThreadingHTTPServer') as listener:
   instance=listener.return_value.__enter__.return_value
   def serve():
    self.assertIsNotNone(data._private_market_data_client);self.assertNotIn(KEY,os.environ)
   instance.serve_forever.side_effect=serve
   server.main(['--port','0'],startup_admission=Admission())
   listener.assert_called_once();instance.serve_forever.assert_called_once()
  self.assertIsNone(data._private_market_data_client)
 def test_missing_or_invalid_private_capability_precedes_listener(self):
  from terminan import server
  for value in (None,'{}','x'*2049,'{"port":1,"port":2}'):
   env={'UNIFIED_MODULE_ID':'terminan','UNIFIED_RELEASE_ID':'r'}
   if value is not None:env[KEY]=value
   with self.subTest(value=value),patch.dict(os.environ,env,clear=True),patch.object(server,'ThreadingHTTPServer') as listener,self.assertRaises(ValueError):server.main(['--port','0'],startup_admission=Admission())
   listener.assert_not_called()

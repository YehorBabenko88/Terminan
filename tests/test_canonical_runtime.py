import unittest,json,http.client,threading,os
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from terminan.server import Handler

class CanonicalRuntimeTests(unittest.TestCase):
    def test_authenticated_health_matches_process_owner_and_hides_token_on_denial(self):
        env=dict(UNIFIED_MODULE_ID='terminan',UNIFIED_MODULE_VERSION='0.1.0',UNIFIED_RELEASE_ID='fixture',UNIFIED_INSTANCE_TOKEN='a'*64)
        with patch.dict(os.environ,env),patch.object(Handler,'log_message'),ThreadingHTTPServer(('127.0.0.1',0),Handler) as server:
            from types import SimpleNamespace
            server.startup_admission=SimpleNamespace(require_current=lambda:True)
            worker=threading.Thread(target=server.serve_forever);worker.start()
            try:
                for headers,expected in (({},503),({'Authorization':'Bearer '+'a'*64},200)):
                    client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=2)
                    try:
                        client.request('GET','/health',headers=headers);response=client.getresponse();raw=response.read();value=json.loads(raw)
                        self.assertEqual(response.status,expected)
                        self.assertFalse(value['trading_authorized']);self.assertFalse(value['execution_authority'])
                        if expected==503:self.assertNotIn(('a'*64).encode(),raw)
                        else:
                            self.assertEqual((value['module_id'],value['version'],value['release_id'],value['instance_token'],value['ready']),('terminan','0.1.0','fixture','a'*64,True))
                    finally:client.close()
            finally:server.shutdown();worker.join(2)

    def test_analytics_endpoint_is_math_owned_and_offline_only(self):
        from terminan.analytics.api import analyze_orderflow
        result=analyze_orderflow(dict(schema='terminan.analytics.orderflow.v1',mode='price',tick_size='0.001',trades=[dict(timestamp_ms=1,price='1.009',volume='2',side='buy')]))
        self.assertEqual(result['rows'][0]['bucket'],'1.009')
        self.assertEqual(result['source_status'],'CALLER_SUPPLIED_UNVERIFIED')
        self.assertFalse(result['execution_authority'])

    def test_managed_start_without_source_admission_cannot_bind(self):
        from terminan.server import main
        with patch.dict(os.environ,{'UNIFIED_MODULE_ID':'terminan'}),patch('terminan.server.ThreadingHTTPServer') as listener:
            with self.assertRaises(ValueError):main(['--port','0'])
            listener.assert_not_called()

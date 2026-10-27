import copy,unittest
from test_r3_evidence import valid as valid3,SHA
from terminan.r4_evidence import check

def valid():
 d=valid3();d['disposed'].update(startupPending=0,retryPending=0,session=dict(state='SESSION_ENDED',closed=True,pending=0,active=0))
 d['r4']=dict(version=1,startupClose=dict(state='VIEW_CLOSED',sessionRequests=0),contractStates=['UNSUPPORTED_TIMEFRAME','UNSUPPORTED_TIMEFRAME','HISTORICAL_ONLY','HISTORICAL_ONLY'],fetch=dict(samples=6,clock='PERFORMANCE_NOW_REQUEST_TO_SETTLED',quantiles=dict(p50=1,p95=2,p99=3)),normalStop=dict(state='SESSION_ENDED',closed=True,requestsStable=True,childExit=0,consoleErrorsAfterEnd=0),unexpectedStop=dict(state='DISCONNECTED',bounded=True,requests=5,retries=5,noRevival=True),limitations=['RENDER_CADENCE_NOT_PRESENTATION_FPS','MAIN_THREAD_CPU_NOT_HOST_TOTAL','RSS_SUM_MAY_COUNT_SHARED_PAGES','OFFLINE_FIXTURES_NO_RUNTIME_AUTHORITY'])
 return d
class R4Evidence(unittest.TestCase):
 def test_valid(self):check(valid(),SHA)
 def test_missing_termination_or_measurement(self):
  for fault in ('missing','ended','identity','samples','latency','timer'):
   d=valid()
   if fault=='missing':del d['r4']
   elif fault=='ended':d['r4']['normalStop']['state']='DISCONNECTED'
   elif fault=='identity':d['r4']['contractStates'][0]='LIVE'
   elif fault=='samples':d['r4']['fetch']['samples']=0
   elif fault=='latency':d['r4']['fetch']['quantiles']['p99']=float('nan')
   else:d['disposed']['session']['pending']=1
   with self.subTest(fault=fault),self.assertRaises((ValueError,KeyError,TypeError)):check(d,SHA)

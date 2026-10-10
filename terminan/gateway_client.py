"""Optional HTTP clients for source-owned loopback gateways; no exchange access."""
import json
import os
from urllib.parse import urlencode
from urllib.request import urlopen

ALLOWED={'grid':('TERMINAN_GRID_GATEWAY',18766),'strattester':('TERMINAN_STRAT_GATEWAY',18767)}

def fetch_source(source,route,params=None):
    if source not in ALLOWED:raise ValueError('unknown source')
    env,port=ALLOWED[source]
    enabled=os.environ.get(env)
    if not enabled:return {'state':'NOT_CONFIGURED'}
    if enabled not in ('127.0.0.1','localhost'):
        raise ValueError('only loopback gateways are supported')
    url='http://127.0.0.1:'+str(port)+route
    if params:url+='?'+urlencode(params)
    with urlopen(url,timeout=3) as response:
        if response.status!=200:raise RuntimeError('source returned error')
        return json.load(response)

"""Pure, bounded, reproducible offline market. No I/O or market connections."""
import hashlib
import json
from .dom import BookEngine, Snapshot, Delta, Level, serializable

VERSION=1
BASE_MS=1767225600000
MAX_STEP=600
SYMBOLS={'BTCUSDT':6500000,'ETHUSDT':350000,'SOLUSDT':15000}
PERIODS={'1m':60000,'5m':300000,'15m':900000,'1h':3600000}
SCENARIOS=('normal','mixed','gap','stale','reconnect','duplicates','out-of-order',
           'partial','unavailable','schema-mismatch','future','nan')

def _mix(seed,index,slot):
    x=(seed ^ (index*2654435761) ^ (slot*2246822519))&0xffffffff
    x=((x^(x>>16))*2246822519)&0xffffffff
    return (x^(x>>13))&0xffffffff

def minute(seed,symbol,index,elapsed=60):
    scale=100 if symbol=='BTCUSDT' else 30 if symbol=='ETHUSDT' else 5
    anchor=SYMBOLS[symbol]+((index%73)-36)*scale//10
    opening=anchor+(_mix(seed,index,0)%41-20)*scale//10
    points=[opening,opening+scale+_mix(seed,index,1)%scale,
            opening-scale-_mix(seed,index,2)%scale,anchor+(_mix(seed,index,3)%41-20)*scale//10]
    elapsed=max(0,min(60,elapsed))
    seen=[points[i] for i in range(4) if i*20<=elapsed]
    if elapsed%20:
        part=elapsed//20
        seen.append(points[part]+(points[part+1]-points[part])*(elapsed%20)//20)
    total=600+_mix(seed,index,4)%600
    return dict(t=index*60000,o=seen[0]/100,h=max(seen)/100,l=min(seen)/100,
                c=seen[-1]/100,v=total*elapsed//60,complete=elapsed==60,
                available_at_ms=index*60000+elapsed*1000)

def candles(seed,symbol,timeframe,as_of_ms):
    period=PERIODS[timeframe];top=as_of_ms//period*period
    result=[]
    for start in range(top-239*period,top+1,period):
        parts=[]
        for stamp in range(start,min(start+period,as_of_ms+1),60000):
            elapsed=min(60,(as_of_ms-stamp)//1000)
            parts.append(minute(seed,symbol,stamp//60000,elapsed))
        if not parts:continue
        result.append(dict(t=start,o=parts[0]['o'],h=max(p['h'] for p in parts),
                           l=min(p['l'] for p in parts),c=parts[-1]['c'],
                           v=sum(p['v'] for p in parts),complete=start+period<=as_of_ms,
                           available_at_ms=min(start+period,as_of_ms)))
    return result

def _book_levels(mid,step,seed):
    return tuple(Level(side,mid+direction*i,1+_mix(seed,step,i+(0 if side=='bid' else 20))%200)
                 for side,direction in [('bid',-1),('ask',1)] for i in range(1,21))

def replay(seed,symbol,step,scenario):
    book=BookEngine(max_levels=80);events=[];accepted=rejected=0
    epoch='synthetic-0'
    mid=round(minute(seed,symbol,BASE_MS//60000,0)['c']*100)
    book.snapshot(Snapshot(epoch,1,_book_levels(mid,0,seed)))
    for tick in range(1,step+1):
        fault=None
        for name,start,end in [('gap',24,32),('stale',48,56),('reconnect',72,80)]:
            if scenario in (name,'mixed') and start<=tick<end:
                fault=name
                if tick==start:
                    if name=='gap':book.delta(Delta(epoch,tick+2,tick+1,()))
                    elif name=='stale':book.stale()
                    else:book.disconnected()
                    events.append(dict(step=tick,event=name.upper(),accepted=False))
                break
        if fault:continue
        mid=round(minute(seed,symbol,(BASE_MS+tick*1000)//60000,tick%60)['c']*100)
        if any(scenario in (name,'mixed') and tick==end for name,start,end in [('gap',24,32),('stale',48,56),('reconnect',72,80)]):
            epoch='synthetic-'+str(tick)
            book.snapshot(Snapshot(epoch,tick+1,_book_levels(mid,tick,seed)))
            accepted+=1;events.append(dict(step=tick,event='FRESH_SNAPSHOT',accepted=True))
            continue
        view=book.view
        erase=tuple(Level(side,price,0) for side,rows in [('bid',view.bids),('ask',view.asks)] for price,qty in rows)
        update=Delta(epoch,tick+1,view.sequence,erase+_book_levels(mid,tick,seed))
        accepted+=bool(book.delta(update))
        if scenario in ('duplicates','mixed') and tick%7==0:
            rejected+=not book.delta(update)
            events.append(dict(step=tick,event='DUPLICATE_IGNORED',accepted=False))
        if scenario in ('out-of-order','mixed') and tick%11==0:
            rejected+=not book.delta(Delta(epoch,max(0,tick-1),max(0,tick-2),()))
            events.append(dict(step=tick,event='LATE_IGNORED',accepted=False))
    dom=serializable(book.view)
    if dom['status']=='LIVE':dom['status']='COHERENT'
    dom.update(mode='SYNTHETIC',tick_size=.01,lot_size=.001)
    return dom,events[-20:],dict(applied=accepted,rejected=int(rejected),replayed=step,queue=0)

def frame(*,seed=17,step=0,symbol='BTCUSDT',timeframe='1m',scenario='normal'):
    if type(seed) is not int or not 0<=seed<=2**31-1:raise ValueError('seed out of range')
    if type(step) is not int or not 0<=step<=MAX_STEP:raise ValueError('step out of range')
    if symbol not in SYMBOLS or timeframe not in PERIODS or scenario not in SCENARIOS:raise ValueError('invalid replay identity')
    as_of=BASE_MS+step*1000
    bars=candles(seed,symbol,timeframe,as_of)
    last=minute(seed,symbol,as_of//60000-1)
    footprint=[]
    for i in range(6):
        volume=last['v']//6 if i<5 else last['v']-5*(last['v']//6)
        buy=_mix(seed,last['t'],i)% (volume+1)
        price=round(last['l']*100)+i
        footprint.append(dict(t=last['t'],price=price/100,buy=buy,sell=volume-buy,
                              delta=2*buy-volume,volume=volume,available_at_ms=last['t']+60000))
    dom,events,counters=replay(seed,symbol,step,scenario)
    result=dict(version=VERSION,mode='SYNTHETIC',seed=seed,step=step,symbol=symbol,
                timeframe=timeframe,period_ms=PERIODS[timeframe],as_of_ms=as_of,
                scenario=scenario,dataset_id=f'synthetic-v1:{seed}:{symbol}',
                candles=bars,footprint=dict(timeframe='1m',state='HISTORICAL_SYNTHETIC',
                    complete_price_levels=True,poc=min(footprint,key=lambda r:(-r['volume'],r['price']))['price'],rows=footprint),dom=dom,events=events,
                counters=counters,source_state='SYNTHETIC',execution='DISABLED',
                coverage=dict(scope='BOUNDED_SYNTHETIC_WINDOW',from_ms=bars[0]['t'],
                              to_ms=as_of,verified=False))
    if scenario=='unavailable':
        result.update(candles=[],source_state='UNAVAILABLE')
        result['footprint']['rows']=[]
        result['footprint']['poc']=None
        result['dom'].update(status='DISCONNECTED',bids=[],asks=[])
    elif scenario=='partial':
        result['candles']=bars[::2];result['source_state']='PARTIAL'
    elif scenario in ('schema-mismatch','future','nan'):
        result.update(candles=[],source_state={'schema-mismatch':'SCHEMA_MISMATCH','future':'FUTURE_LEAKAGE','nan':'INVALID_DATA'}[scenario])
        result['footprint']['rows']=[]
        result['footprint']['poc']=None
    result['frame_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return result

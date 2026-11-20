"""Bounded offline analytics DTO endpoint; no market acquisition or execution."""
from dataclasses import asdict
from .orderflow_adapters import from_records
from .orderflow_aggregation import aggregate_by_time,aggregate_by_price
from .orderflow_view import make_rows

def analyze_orderflow(request):
    if type(request) is not dict or request.get('schema')!='terminan.analytics.orderflow.v1':
        raise ValueError('INVALID_ANALYTICS_REQUEST')
    mode=request.get('mode')
    parameter='interval_ms' if mode=='time' else 'tick_size' if mode=='price' else None
    if parameter is None or set(request)!={'schema','mode','trades',parameter}:
        raise ValueError('INVALID_ANALYTICS_FIELDS')
    rows=request['trades']
    if type(rows) is not list or len(rows)>20000:
        raise ValueError('ANALYTICS_ROW_BUDGET_EXCEEDED')
    if any(type(row) is not dict or set(row)!={'timestamp_ms','price','volume','side'} for row in rows):
        raise ValueError('INVALID_ANALYTICS_TRADE')
    trades=from_records(rows)
    buckets=(aggregate_by_time(trades,request[parameter]) if mode=='time'
             else aggregate_by_price(trades,request[parameter]))
    return dict(schema='terminan.analytics.result.v1',mode=mode,
        rows=[asdict(row) for row in make_rows(buckets)],
        source_status='CALLER_SUPPLIED_UNVERIFIED',execution_authority=False,trading_authorized=False)


def analyze_historical(request):
    """Canonical bounded read-only history/research request; no caller clock override."""
    if type(request) is not dict or set(request)!={'schema','mode','payload','decision_ms'} or request['schema']!='terminan.analytics.historical.v1':
        raise ValueError('INVALID_HISTORICAL_ANALYTICS_REQUEST')
    if request['mode']=='ohlcv':
        from .ohlcv_research import analyze_ohlcv_research
        return analyze_ohlcv_research(request['payload'],decision_ms=request['decision_ms'])
    if request['mode']=='market_history':
        from .market_history import analyze_market_history
        return analyze_market_history(request['payload'],decision_ms=request['decision_ms'])
    raise ValueError('INVALID_HISTORICAL_ANALYTICS_MODE')

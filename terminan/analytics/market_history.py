"""Explicit historical versions sharing one pure validation/projection core."""
import copy
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from .core import Candle,untouched_levels
from ..history_protocol import validate_minute_history,DECLARATIONS,_digest
_EPOCH=datetime(1970,1,1,tzinfo=timezone.utc)

def analyze_market_history(payload,*,decision_ms):
    try:return _analyze(payload,decision_ms,version='v1.1')
    except (KeyError,TypeError,OverflowError,RecursionError) as exc:raise ValueError('INVALID_MARKET_HISTORY') from exc

def analyze_market_history_v12(payload,*,decision_ms,expected_snapshot_id,catalog):
    try:return _analyze(payload,decision_ms,version='v1.2',expected_snapshot_id=expected_snapshot_id,catalog=catalog)
    except (KeyError,TypeError,OverflowError,RecursionError) as exc:raise ValueError('INVALID_MARKET_HISTORY_V12') from exc

def _analyze(payload,decision,*,version,expected_snapshot_id=None,catalog=None):
    p,decision,expected_snapshot_id=validate_minute_history(payload,decision,version=version,expected_snapshot_id=expected_snapshot_id,catalog=catalog)
    q,source,rows=p['request'],p['source'],p['rows']
    start,end,asof=q['start_ms'],q['end_ms'],q['as_of_ms']
    known = [r for r in rows if r['event_end_ms'] <= decision and r['available_at_ms'] <= decision]
    gap = any(r['event_start_ms'] != start+i*60000 for i, r in enumerate(known))
    candles = [Candle(_EPOCH+timedelta(milliseconds=r['event_start_ms']),
                      *(Decimal(str(r[k])) for k in ('high', 'low', 'open', 'close', 'volume'))) for r in known]
    levels = [] if gap else untouched_levels(candles, '1m')
    clocks = {c.start: r for c, r in zip(candles, known)}
    # A surviving level requires all later analyzed wicks; availability binds that
    # entire analysis prefix, not only the candle that first introduced the level.
    available = max((r['available_at_ms'] for r in known), default=None)
    result = {'schema': 'terminan.market.history.analysis.v1',
            'dataset_id': p['dataset_id'], 'dataset_fingerprint': p['dataset_fingerprint'],
            'source': copy.deepcopy(source), 'evidence_class': p['evidence_class'],
            'symbol': q['symbol'], 'venue': q['venue'], 'market_type': q['market_type'],
            'timeframe': '1m', 'units': copy.deepcopy(q['units']), 'decision_ms': decision,
            'snapshot_as_of_ms': asof, 'window_start_ms': start, 'window_end_ms': end,
            'quality_status': 'UNKNOWN', 'source_authenticity': 'NOT_EVALUATED',
            'coverage_status': 'GAP' if gap else 'UNAVAILABLE' if not known else 'PARTIAL' if len(known) < len(rows) else 'DECLARED_COMPLETE_UNVERIFIED',
            'excluded_rows': len(rows)-len(known), 'rows': copy.deepcopy(known),
            'candles': [{'event_start_ms': r['event_start_ms'], 'event_end_ms': r['event_end_ms'],
                         'available_at_ms': r['available_at_ms'],
                         **{k: str(getattr(c, k)) for k in ('open', 'high', 'low', 'close', 'volume')},
                         **({'turnover':str(Decimal(str(r['turnover'])))} if version=='v1.2' else {})} for c, r in zip(candles, known)],
            'levels': [{'price': str(level.price), 'kind': level.kind, 'timeframe': level.timeframe,
                        'source_start_ms': clocks[level.source_start]['event_start_ms'],
                        'available_at_ms': available} for level in levels],
            'execution_authority': False, 'trading_authorized': False, 'training_authorized': False}

    if version=='v1.2':
        result.update(schema='terminan.market.history.analysis.v1.2',**DECLARATIONS,
            expected_snapshot_id=expected_snapshot_id,point_in_time_availability='DECLARED_UNVERIFIED',h_b_eligible=False)
        result['analysis_fingerprint']=_digest(result)
    return result

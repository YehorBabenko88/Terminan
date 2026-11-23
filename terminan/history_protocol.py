"""Closed immutable historical wire admission; no Data SDK import or IO.

Hashes bind declared content and caller policy, never source/PIT authority.
Business numerics and financial predicates belong solely to canonical Math.
"""
from decimal import Decimal
from math import isfinite
import hashlib,json,math,re
from hmac import compare_digest

DECLARATIONS={'turnover_basis':'EXECUTED_TRADE_PRICE_TIMES_QUANTITY_SUM',
 'availability_basis':'CALLER_DECLARED_NOT_COMMIT_OR_PIT',
 'financial_encoding':'FINITE_BINARY64_DTO_FROM_EXACT_DECIMAL_ACCUMULATION',
 'source_authentication':'NOT_EVALUATED'}
REQUEST_KEYS={'schema','venue','market_type','symbol','start_ms','end_ms','as_of_ms','max_age_ms','units'}
TRUST_KEYS={'schema','identity','source_revision','epoch','receipts','receipt_pins','evidence_class'}
RECEIPT_KEYS={'schema','record_api_version','dataset_schema','fingerprint','venue','available_at_ms','watermark_ms','complete','units','evidence_class','turnover_basis'}
ROLLUP_ROW_KEYS={'open','high','low','close','volume','turnover','event_start_ms','event_end_ms','available_at_ms','watermark_ms'}
_MAX_CLOCK = 2**53 - 1
_ROW_FIELDS = {'open', 'high', 'low', 'close', 'volume', 'event_start_ms',
               'event_end_ms', 'available_at_ms', 'revision', 'source_event_start_ms',
               'source_event_end_ms', 'watermark_ms', 'source_receipt_hash'}


def _clock(value):
    if type(value) is not int or not 0 <= value <= _MAX_CLOCK:
        raise ValueError('INVALID_CLOCK')
    return value


def _hash(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('INVALID_DIGEST')
    return value


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _fields(value, fields):
    if type(value) is not dict or set(value) != fields:
        raise ValueError('INVALID_FIELDS')


def _snapshot_literal(value,*,max_bytes=8388608):
    remaining=max_bytes;nodes=0
    def charge(size):
        nonlocal remaining
        remaining-=size
        if remaining<0:raise ValueError('HISTORY_PROTOCOL_BYTE_BUDGET')
    def copy(item,depth):
        nonlocal nodes
        nodes+=1
        if nodes>250000 or depth>16:raise ValueError('HISTORY_PROTOCOL_GRAPH_BUDGET')
        kind=type(item)
        if item is None or kind is bool or kind is int or kind is float or kind is str:
            if kind is int and item.bit_length()>1024:raise ValueError('HISTORY_PROTOCOL_INTEGER_BUDGET')
            if kind is str and len(item)>max_bytes:raise ValueError('HISTORY_PROTOCOL_STRING_BUDGET')
            try:raw=json.dumps(item,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
            except (ValueError,TypeError,OverflowError):raise ValueError('HISTORY_PROTOCOL_LITERAL_VALUE_REQUIRED') from None
            charge(len(raw));return item
        if kind is list or kind is tuple:
            if len(item)>250000:raise ValueError('HISTORY_PROTOCOL_GRAPH_BUDGET')
            charge(2+max(0,len(item)-1));out=[copy(child,depth+1) for child in item]
            return tuple(out) if kind is tuple else out
        if kind is dict:
            if len(item)>250000:raise ValueError('HISTORY_PROTOCOL_GRAPH_BUDGET')
            if any(type(key) is not str or not 1<=len(key)<=128 for key in item):raise ValueError('HISTORY_PROTOCOL_LITERAL_KEY_REQUIRED')
            charge(2+max(0,len(item)-1)+len(item));out={}
            for key,child in item.items():
                charge(len(json.dumps(key,ensure_ascii=True).encode('ascii')));out[key]=copy(child,depth+1)
            return out
        raise ValueError('HISTORY_PROTOCOL_LITERAL_VALUE_REQUIRED')
    return copy(value,0)

def _units(value):
    if type(value) is not dict or len(value)!=3 or any(type(k) is not str or k not in ('price','volume','turnover') for k in value):raise ValueError('HISTORY_PROTOCOL_EXPLICIT_QUOTE_UNITS_REQUIRED')
    if any(type(value[k]) is not str or re.fullmatch('[A-Z0-9][A-Z0-9_.-]{0,31}',value[k]) is None for k in ('volume','turnover')):raise ValueError('HISTORY_PROTOCOL_LITERAL_UNIT_REQUIRED')
    if type(value['price']) is not str or value['price']!=value['turnover']+'/'+value['volume']:raise ValueError('HISTORY_PROTOCOL_UNIT_RELATION_REQUIRED')
    return dict(value)

def _number(value):
    if type(value) is not int and type(value) is not float:raise ValueError('HISTORY_LITERAL_NUMBER')
    from market_math import lossless_nonnegative_binary64_valid
    if lossless_nonnegative_binary64_valid(value) is not True:raise ValueError('HISTORY_LITERAL_NUMBER')
    return value

def _financial_row(row):
    from market_math import executed_notional_consistent,candle_ohlcv_turnover_valid
    values=tuple(_number(row[k]) for k in ('open','high','low','close','volume','turnover'))
    if executed_notional_consistent(values[5],values[4]) is not True:raise ValueError('HISTORY_ZERO_NOTIONAL_IDENTITY')
    if candle_ohlcv_turnover_valid(*(Decimal(str(v)) for v in values[:5]),turnover=Decimal(str(values[5]))) is not True:
        raise ValueError('HISTORY_FINANCIAL_DOMAIN')

def _catalog_entry(pin,catalog):
    _hash(pin)
    if type(catalog) is not dict:raise ValueError('HISTORY_CATALOG_REQUIRED')
    entry=catalog.get(pin)
    _fields(entry,{'schema','request','trust','revisions','dataset_id','dataset_fingerprint'})
    if entry['schema']!='market_data.history.catalog-entry.v1.2' or _digest(entry)!=pin:raise ValueError('HISTORY_CATALOG_PIN')
    q,t,revisions=entry['request'],entry['trust'],entry['revisions']
    _fields(q,REQUEST_KEYS);_fields(t,TRUST_KEYS)
    if q['schema']!='market_data.history.request.v1.2' or t['schema']!='market_data.history.trust.v1.2' or t['evidence_class']!='HISTORICAL':raise ValueError('HISTORY_CATALOG_VERSION')
    for key in ('venue','market_type','symbol'):
        if type(q[key]) is not str or not q[key]:raise ValueError('HISTORY_CATALOG_IDENTITY')
    for key in ('identity','source_revision','epoch'):
        if type(t[key]) is not str or not t[key]:raise ValueError('HISTORY_CATALOG_SOURCE')
    start,end,asof,age=(_clock(q[k]) for k in ('start_ms','end_ms','as_of_ms','max_age_ms'))
    count=(end-start)//60000
    if start%60000 or end%60000 or not 1<=count<=2000 or not end<=asof<=end+age:raise ValueError('HISTORY_CATALOG_BOUNDS')
    _units(q['units']);_hash(entry['dataset_id']);_hash(entry['dataset_fingerprint'])
    if type(revisions) is not list or len(revisions)!=count:raise ValueError('HISTORY_REVISION_COUNT')
    for revision in revisions:_hash(revision)
    if len(set(revisions))!=count:raise ValueError('HISTORY_REVISION_DUPLICATE')
    if type(t['receipts']) is not dict or type(t['receipt_pins']) is not dict or set(t['receipts'])!=set(revisions) or set(t['receipt_pins'])!=set(revisions):raise ValueError('HISTORY_RECEIPT_ROSTER')
    for index,revision in enumerate(revisions):
        receipt=t['receipts'][revision];_fields(receipt,RECEIPT_KEYS)
        _fields(receipt['record_api_version'],{'major','minor'})
        if (receipt['schema']!='market_data.history.receipt.v1.2' or receipt['dataset_schema']!='market_data.dataset.v1.2'
            or type(receipt['record_api_version']['major']) is not int or type(receipt['record_api_version']['minor']) is not int
            or receipt['record_api_version']!={'major':1,'minor':2} or receipt['fingerprint']!=revision
            or receipt['venue']!=q['venue'] or receipt['units']!=q['units'] or receipt['evidence_class']!='HISTORICAL'
            or receipt['turnover_basis']!=DECLARATIONS['turnover_basis'] or receipt['complete'] is not True):raise ValueError('HISTORY_RECEIPT_DECLARATION')
        known,watermark=_clock(receipt['available_at_ms']),_clock(receipt['watermark_ms'])
        if not start+(index+1)*60000<=watermark<=known<=asof or _hash(t['receipt_pins'][revision])!=_digest(receipt):raise ValueError('HISTORY_RECEIPT_PIN_OR_CLOCK')
    return entry

def _bind_minute_catalog(p,pin,catalog):
    entry=_catalog_entry(pin,catalog);t=entry['trust']
    if (p['request']!=entry['request'] or p['source']!={k:t[k] for k in ('identity','source_revision','epoch')}
        or any(p[k]!=entry[k] for k in ('dataset_id','dataset_fingerprint'))
        or [row['revision'] for row in p['rows']]!=entry['revisions']):raise ValueError('HISTORY_PARENT_PIN')
    for row in p['rows']:
        receipt=t['receipts'][row['revision']]
        if (row['source_receipt_hash']!=t['receipt_pins'][row['revision']] or row['available_at_ms']!=receipt['available_at_ms'] or row['watermark_ms']!=receipt['watermark_ms']):raise ValueError('HISTORY_PARENT_RECEIPT')

def validate_minute_history(payload,decision,*,version,expected_snapshot_id=None,catalog=None):
    if type(version) is not str or version not in ('v1.1','v1.2'):raise ValueError('HISTORY_VERSION')
    p,decision,expected_snapshot_id,catalog=_snapshot_literal((payload,decision,expected_snapshot_id,catalog))
    _clock(decision)
    _fields(p, {'schema', 'request', 'source', 'evidence_class', 'rows',
                'source_receipts', 'execution_authority', 'trading_authorized',
                'watermark_ms', 'dataset_id', 'dataset_fingerprint'} | (set(DECLARATIONS) if version == 'v1.2' else set()))
    if p['schema'] != ('market_data.history.v1.2' if version == 'v1.2' else 'market_data.history.v1.1') or p['execution_authority'] is not False or p['trading_authorized'] is not False:
        raise ValueError('INVALID_CONTRACT')
    if p['evidence_class'] not in ('SYNTHETIC', 'HISTORICAL'):
        raise ValueError('INVALID_EVIDENCE_CLASS')
    q, source, rows = p['request'], p['source'], p['rows']
    _fields(q, {'schema', 'venue', 'market_type', 'symbol', 'start_ms', 'end_ms',
                'as_of_ms', 'max_age_ms', 'units'})
    _fields(source, {'identity', 'source_revision', 'epoch'})
    if any(type(source[k]) is not str or not 1 <= len(source[k]) <= 256 for k in source):
        raise ValueError('INVALID_SOURCE')
    if not re.fullmatch('[0-9a-f]{40}', source['source_revision']):
        raise ValueError('INVALID_SOURCE_REVISION')
    if q['schema'] != ('market_data.history.request.v1.2' if version == 'v1.2' else 'market_data.history.request.v1') or q['venue'] != 'bybit' or q['market_type'] != 'linear':
        raise ValueError('UNSUPPORTED_MARKET')
    if type(q['symbol']) is not str or not re.fullmatch('[A-Z0-9]{1,24}USDT', q['symbol']):
        raise ValueError('UNSUPPORTED_SYMBOL')
    if version == 'v1.1' and q['units'] != {'price': 'USDT/'+q['symbol'][:-4], 'volume': q['symbol'][:-4]}:
        raise ValueError('UNSUPPORTED_UNITS')
    for key in ('start_ms', 'end_ms', 'as_of_ms', 'max_age_ms'):
        _clock(q[key])
    start, end, asof = q['start_ms'], q['end_ms'], q['as_of_ms']
    if start % 60000 or end % 60000 or not 1 <= (end-start)//60000 <= 2000:
        raise ValueError('INVALID_WINDOW')
    if not end <= asof or asof-end > q['max_age_ms'] or decision > asof or max(0, decision-end) > q['max_age_ms']:
        raise ValueError('INVALID_AS_OF')
    if type(rows) is not list or len(rows) != (end-start)//60000:
        raise ValueError('INCOMPLETE_EXPORT')
    if type(p['source_receipts']) is not list or len(p['source_receipts']) != len(rows):
        raise ValueError('INVALID_RECEIPTS')
    revisions = set()
    for i, row in enumerate(rows):
        _fields(row, _ROW_FIELDS | ({'turnover'} if version == 'v1.2' else set()))
        for k in ('event_start_ms', 'event_end_ms', 'available_at_ms',
                  'source_event_start_ms', 'source_event_end_ms', 'watermark_ms'):
            _clock(row[k])
        lo, hi = start+i*60000, start+(i+1)*60000
        if (row['event_start_ms'] != lo or row['event_end_ms'] != hi or
            not lo <= row['source_event_start_ms'] <= row['source_event_end_ms'] < hi or
            not hi <= row['watermark_ms'] <= row['available_at_ms'] <= asof):
            raise ValueError('INVALID_ROW_CLOCKS')
        if version=='v1.1':
            for k in ('open', 'high', 'low', 'close', 'volume'):
                if type(row[k]) not in (int, float) or not math.isfinite(row[k]):
                    raise ValueError('INVALID_OHLCV')
            if not 0 < row['low'] <= min(row['open'], row['close']) <= max(row['open'], row['close']) <= row['high'] or row['volume'] < 0:
                raise ValueError('INVALID_OHLCV')
        revision = _hash(row['revision'])
        if revision in revisions:
            raise ValueError('DUPLICATE_REVISION')
        revisions.add(revision)
        if _hash(row['source_receipt_hash']) != _hash(p['source_receipts'][i]):
            raise ValueError('RECEIPT_MISMATCH')
    if _clock(p['watermark_ms']) != max(row['watermark_ms'] for row in rows):
        raise ValueError('WATERMARK_MISMATCH')
    if len(_canonical(p)) > 8*1024*1024:
        raise ValueError('BYTE_LIMIT')
    content = {'schema': 'market_data.dataset.v1.2' if version == 'v1.2' else 'market_data.dataset.v1.1', 'source': source,
               'identity': {k: q[k] for k in ('venue', 'market_type', 'symbol', 'units')},
               'timeframe': '1m', 'representation': 'historical_aggregate',
               'evidence_class': p['evidence_class'], 'rows': rows, 'source_receipts': p['source_receipts']}
    if version == 'v1.2': content.update({key:p[key] for key in DECLARATIONS})
    if _hash(p['dataset_id']) != _digest(content) or _hash(p['dataset_fingerprint']) != _digest({k: v for k, v in p.items() if k != 'dataset_fingerprint'}):
        raise ValueError('INTEGRITY_MISMATCH')

    if version=='v1.2':
        _units(q['units'])
        if p['evidence_class']!='HISTORICAL' or any(p[k]!=v for k,v in DECLARATIONS.items()):raise ValueError('HISTORY_DECLARATION')
        _bind_minute_catalog(p,expected_snapshot_id,catalog)
        for row in rows:_financial_row(row)
    return p,decision,expected_snapshot_id

canonical_json=_canonical
# MarketData v2 multipin calendar widths. The HTTP route remains fenced until
# an authenticated provider supplies the expected rollup pins.
_DAY = 86_400_000
_MARKET_DATA_LEVEL_WIDTHS = {"1h": 3_600_000, "4h": 14_400_000, "1d": _DAY, "1w": 7 * _DAY}
_MAX_MARKET_DATA_LEVEL_CANDLES = 1000
_MAX_MARKET_DATA_SERIES_CANDLES = 32
_MAX_MARKET_DATA_SERIES_SPAN_MS = 14 * _DAY
_MARKET_DATA_MAX_TIMESTAMP = 2**53 - 1


def _fingerprint(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _valid_parent(parent):
    return (type(parent) is dict and type(parent.get("dataset_id")) is str
            and bool(parent["dataset_id"]) and _fingerprint(parent.get("dataset_fingerprint")))


def _market_data_window_width(timeframe, start_ms, end_ms, as_of_ms):
    if type(timeframe) is not str or timeframe not in _MARKET_DATA_LEVEL_WIDTHS:
        raise ValueError("unsupported MarketData levels timeframe")
    width = _MARKET_DATA_LEVEL_WIDTHS[timeframe]
    anchor = 4 * _DAY if timeframe == "1w" else 0
    if (any(type(value) is not int for value in (start_ms, end_ms, as_of_ms))
            or not 0 <= start_ms < end_ms <= as_of_ms <= _MARKET_DATA_MAX_TIMESTAMP
            or (start_ms - anchor) % width or (end_ms - anchor) % width
            or (end_ms - start_ms) // width > _MAX_MARKET_DATA_LEVEL_CANDLES):
        raise ValueError("invalid MarketData levels window")
    return width



def legacy_rollup_candles(snapshot, *, trusted_fingerprint, symbol, market_type,
                       timeframe, start_ms, end_ms, as_of_ms):
    """Map a pinned MarketData rollup to Math input after the caller authenticates its pin.

    The trusted fingerprint comes from independent source admission, never from
    the same response as the snapshot. This function does not authenticate a
    transport or qualify a bare MarketData HTTP response.
    """
    snapshot,trusted_fingerprint,symbol,market_type,timeframe,start_ms,end_ms,as_of_ms=_snapshot_literal((snapshot,trusted_fingerprint,symbol,market_type,timeframe,start_ms,end_ms,as_of_ms))
    if not _fingerprint(trusted_fingerprint):
        raise ValueError("independent MarketData fingerprint required")
    if (type(symbol) is not str or not re.fullmatch(r"[A-Z0-9]{2,30}", symbol)
            or type(market_type) is not str or not market_type):
        raise ValueError("invalid MarketData levels instrument")
    width = _market_data_window_width(timeframe, start_ms, end_ms, as_of_ms)

    if (type(snapshot) is not dict or snapshot.get("schema") not in
            ("market_data.history.rollup.v1", "market_data.history.rollup.v2", "market_data.history.rollup.v3")
            or snapshot.get("evidence_class") != "HISTORICAL"
            or snapshot.get("timeframe") != timeframe
            or type(snapshot.get("source")) is not dict
            or snapshot.get("dataset_fingerprint") != trusted_fingerprint):
        raise ValueError("MarketData rollup does not match trusted selection")
    request = snapshot.get("request")
    expected = {"venue": "bybit", "symbol": symbol, "market_type": market_type,
                "start_ms": start_ms, "end_ms": end_ms}
    if (type(request) is not dict or any(type(request.get(key)) is not type(value)
                                       or request[key] != value for key, value in expected.items())):
        raise ValueError("MarketData rollup request mismatch")
    if snapshot["schema"] == "market_data.history.rollup.v1":
        if (timeframe != "1h" or type(request.get("as_of_ms")) is not int
                or request["as_of_ms"] != as_of_ms
                or not _valid_parent({"dataset_id": snapshot.get("parent_dataset_id"),
                                      "dataset_fingerprint": snapshot.get("parent_dataset_fingerprint")})):
            raise ValueError("invalid MarketData single-pin lineage")
    else:
        parents = snapshot.get("parents")
        span = end_ms - start_ms
        sequence = snapshot["schema"] == "market_data.history.rollup.v3"
        if sequence:
            if (request.get("schema") != "market_data.history.selection.v4"
                    or span > min(_MAX_MARKET_DATA_SERIES_CANDLES * width, _MAX_MARKET_DATA_SERIES_SPAN_MS)):
                raise ValueError("invalid MarketData levels series window")
        elif span != width:
            raise ValueError("invalid MarketData single-candle window")
        if (type(snapshot.get("as_of_ms")) is not int
                or snapshot["as_of_ms"] != as_of_ms or request.get("timeframe") != timeframe
                or type(snapshot.get("units")) is not dict or type(parents) is not list
                or not 1 <= len(parents) <= (16 if sequence else 8)
                or any(not _valid_parent(parent) or not _fingerprint(parent.get("snapshot_id"))
                       for parent in parents)):
            raise ValueError("invalid MarketData multipin lineage")
        pins = [parent["snapshot_id"] for parent in parents]
        if request.get("snapshot_ids") != pins or len(set(pins)) != len(pins):
            raise ValueError("invalid MarketData parent order")
        if sequence and any(
            type(record.get(key)) is not str or not record[key]
            for record, fields in ((snapshot["source"], ("identity", "source_revision", "epoch")),
                                   (snapshot["units"], ("price", "volume")))
            for key in fields
        ):
            raise ValueError("MarketData levels series source lineage is incomplete")
    rows = snapshot.get("rows")
    if type(rows) is not list or len(rows) != (end_ms - start_ms) // width:
        raise ValueError("incomplete MarketData levels window")
    payload = canonical_json({key: value for key, value in snapshot.items()
                              if key != "dataset_fingerprint"})
    if len(payload) > 2_097_152 or not compare_digest(hashlib.sha256(payload).hexdigest(), trusted_fingerprint):
        raise ValueError("MarketData rollup fingerprint mismatch")

    return _level_rows(rows,start_ms,width,as_of_ms,version='legacy')

def _level_rows(rows,start_ms,width,as_of_ms,*,version):
    for index, row in enumerate(rows):
        if version=='v1.2':
            _fields(row,ROLLUP_ROW_KEYS)
            _financial_row(row)
        lower = start_ms + index * width
        upper = lower + width
        if (type(row) is not dict or row.get("complete", True) is not True
                or any(type(row.get(field)) is not int for field in
                       ("event_start_ms", "event_end_ms", "available_at_ms", "watermark_ms"))
                or row["event_start_ms"] != lower or row["event_end_ms"] != upper
                or not upper <= row["watermark_ms"] <= row["available_at_ms"] <= as_of_ms):
            raise ValueError("incomplete or unavailable MarketData candle")
        high, low = row.get("high"), row.get("low")
        try:
            valid = all(type(price) in (int, float) and isfinite(price)
                        and price > 0 for price in (high, low))
        except OverflowError:
            valid = False
        if not valid or high < low:
            raise ValueError("invalid MarketData candle prices")
    return [{"t":row["event_start_ms"],"h":row["high"],"l":row["low"],"complete":True} for row in rows]


_V12_WINDOW_WIDTHS={'5m':300000,'15m':900000,'1h':3600000}

def _selection_v12(s):
    if type(s) is not dict:raise ValueError('HISTORY_SELECTION')
    operation=s.get('operation')
    if type(operation) is not str or operation not in ('minutes','window','multipin','series'):raise ValueError('HISTORY_OPERATION')
    multi=operation in ('multipin','series')
    keys={'schema','operation','venue','market_type','symbol','start_ms','end_ms','snapshot_ids' if multi else 'snapshot_id'}
    if operation!='minutes':keys.add('timeframe')
    _fields(s,keys)
    if s['schema']!='market_data.history.selection.v1.2':raise ValueError('HISTORY_SELECTION_SCHEMA')
    for key in ('venue','market_type','symbol'):
        if type(s[key]) is not str or not s[key]:raise ValueError('HISTORY_SELECTION_IDENTITY')
    start,end=_clock(s['start_ms']),_clock(s['end_ms'])
    if start%60000 or end%60000 or start>=end:raise ValueError('HISTORY_SELECTION_BOUNDS')
    pins=s['snapshot_ids'] if multi else [s['snapshot_id']]
    if type(pins) is not list or not 1<=len(pins)<=(16 if operation=='series' else 8 if multi else 1):raise ValueError('HISTORY_SELECTION_PINS')
    for pin in pins:_hash(pin)
    if len(set(pins))!=len(pins):raise ValueError('HISTORY_SELECTION_DUPLICATE')
    if not multi and end-start>2000*60000:raise ValueError('HISTORY_SELECTION_BOUNDS')
    if operation=='minutes':return pins,None
    widths=_MARKET_DATA_LEVEL_WIDTHS if multi else _V12_WINDOW_WIDTHS
    tf=s['timeframe']
    if type(tf) is not str or tf not in widths:raise ValueError('HISTORY_SELECTION_TIMEFRAME')
    width=widths[tf];anchor=4*_DAY if tf=='1w' else 0
    maximum=min(32*width,14*_DAY) if operation=='series' else width if multi else 2000*60000
    if (start-anchor)%width or (end-anchor)%width or not width<=end-start<=maximum:raise ValueError('HISTORY_SELECTION_ALIGNMENT')
    return pins,width

def validate_rollup_v12(snapshot,*,trusted_fingerprint,selection,catalog,as_of_ms,options):
    # Entire graph, including unused catalog keys/leaves and all options, is
    # copied before any get/set/hash/equality or numerical owner callback.
    p,trusted_fingerprint,s,catalog,expected_asof,options=_snapshot_literal((snapshot,trusted_fingerprint,selection,catalog,as_of_ms,options))
    _hash(trusted_fingerprint);pins,width=_selection_v12(s)
    if s['operation']=='minutes':raise ValueError('HISTORY_ROLLUP_OPERATION')
    _fields(p,{'schema','operation','selection','timeframe','source','units','as_of_ms','evidence_class','parents','rows','execution_authority','trading_authorized','dataset_fingerprint',*DECLARATIONS})
    if (p['schema']!='market_data.history.rollup.v1.2' or p['operation']!=s['operation'] or p['selection']!=s or p['timeframe']!=s['timeframe']
        or p['evidence_class']!='HISTORICAL' or p['execution_authority'] is not False or p['trading_authorized'] is not False
        or any(p[k]!=v for k,v in DECLARATIONS.items())):raise ValueError('HISTORY_ROLLUP_DECLARATION')
    _units(p['units']);_fields(p['source'],{'identity','source_revision','epoch'})
    if any(type(v) is not str or not v for v in p['source'].values()):raise ValueError('HISTORY_ROLLUP_SOURCE')
    asof=_clock(p['as_of_ms'])
    if expected_asof is not None and _clock(expected_asof)!=asof:raise ValueError('HISTORY_ROLLUP_ASOF')
    if asof<s['end_ms']:raise ValueError('HISTORY_ROLLUP_ASOF')
    if p['dataset_fingerprint']!=trusted_fingerprint or _digest({k:v for k,v in p.items() if k!='dataset_fingerprint'})!=trusted_fingerprint:raise ValueError('HISTORY_ROLLUP_FINGERPRINT')
    if type(options) is not dict or set(options) not in (set(),{'decision_ms','tick_size','max_levels'}):raise ValueError('HISTORY_OPTIONS')
    if options:
        if _clock(options['decision_ms'])>asof:raise ValueError('HISTORY_DECISION')
        if type(options['tick_size']) is not int and type(options['tick_size']) is not float:raise ValueError('HISTORY_TICK_LITERAL')
        if type(options['max_levels']) is not int or not 1<=options['max_levels']<=2000:raise ValueError('HISTORY_MAX_LEVELS')
    parents,rows=p['parents'],p['rows']
    if type(parents) is not list or len(parents)!=len(pins):raise ValueError('HISTORY_ROLLUP_PARENTS')
    if type(rows) is not list or len(rows)!=(s['end_ms']-s['start_ms'])//width:raise ValueError('HISTORY_ROLLUP_COVERAGE')
    cursor=s['start_ms'];receipt_clocks=[]
    for pin,parent in zip(pins,parents):
        _fields(parent,{'snapshot_id','dataset_id','dataset_fingerprint'})
        if parent['snapshot_id']!=pin:raise ValueError('HISTORY_PARENT_ORDER')
        entry=_catalog_entry(pin,catalog);q,t=entry['request'],entry['trust']
        if (any(parent[k]!=entry[k] for k in ('dataset_id','dataset_fingerprint')) or q['start_ms']!=cursor or q['end_ms']>s['end_ms']
            or any(q[k]!=s[k] for k in ('venue','market_type','symbol')) or q['units']!=p['units'] or q['as_of_ms']!=asof
            or p['source']!={k:t[k] for k in ('identity','source_revision','epoch')}):raise ValueError('HISTORY_PARENT_LINEAGE')
        for revision in entry['revisions']:
            a=t['receipts'][revision];receipt_clocks.append((a['available_at_ms'],a['watermark_ms']))
        cursor=q['end_ms']
    if cursor!=s['end_ms']:raise ValueError('HISTORY_PARENT_GAP')
    minutes=width//60000
    for index,row in enumerate(rows):
        _fields(row,ROLLUP_ROW_KEYS)
        clocks=receipt_clocks[index*minutes:(index+1)*minutes]
        if len(clocks)!=minutes or row['available_at_ms']!=max(a for a,w in clocks) or row['watermark_ms']!=max(w for a,w in clocks):raise ValueError('HISTORY_ALL_PARENT_AVAILABILITY')
    # The trusted fingerprint binds declared turnover; absent parent amounts
    # cannot establish an independently recomputed sum or source authenticity.
    _level_rows(rows,s['start_ms'],width,asof,version='v1.2')
    if options:_number(options['tick_size'])
    return p,options

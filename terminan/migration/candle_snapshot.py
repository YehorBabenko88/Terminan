"""Explicit read-only frozen candle source import, never an active data service."""
from .research_results import open_frozen_sqlite_snapshot
from ..data import validate

def read_candle_snapshot(source, symbol, timeframe='1m', limit=300):
    validate(symbol,timeframe)
    if type(limit) is not int or not 1<=limit<=1000:raise ValueError('invalid row bound')
    with open_frozen_sqlite_snapshot(source) as db:
        rows=db.execute('SELECT open_time,open,high,low,close,volume FROM candles WHERE symbol=? AND timeframe=? ORDER BY open_time DESC LIMIT ?', (symbol,timeframe,limit)).fetchall()
    return [dict(zip(('t','o','h','l','c','v'),row)) for row in reversed(rows)]

def read_instrument_snapshot(source):
    with open_frozen_sqlite_snapshot(source) as db:
        return [row[0] for row in db.execute('SELECT DISTINCT symbol FROM candles ORDER BY symbol LIMIT 2000')]

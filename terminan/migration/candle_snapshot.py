"""Explicit read-only frozen candle source import, never an active data service."""
from contextlib import closing
from pathlib import Path
import sqlite3
from ..data import validate

def read_candle_snapshot(source, symbol, timeframe='1m', limit=300):
    validate(symbol,timeframe)
    if type(limit) is not int or not 1<=limit<=1000:raise ValueError('invalid row bound')
    path=Path(source).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
        db.execute('PRAGMA query_only=ON')
        rows=db.execute('SELECT open_time,open,high,low,close,volume FROM candles WHERE symbol=? AND timeframe=? ORDER BY open_time DESC LIMIT ?', (symbol,timeframe,limit)).fetchall()
    return [dict(zip(('t','o','h','l','c','v'),row)) for row in reversed(rows)]

def read_instrument_snapshot(source):
    path=Path(source).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
        db.execute('PRAGMA query_only=ON')
        return [row[0] for row in db.execute('SELECT DISTINCT symbol FROM candles ORDER BY symbol LIMIT 2000')]

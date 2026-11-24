"""Ownership-aware annotation reconciliation, ported from Meta PR82 level_sync.

Only canonical Terminan signatures are managed. Uncertain writes propagate;
retrying replace always rereads the terminal. No durable-store duplicate.
"""
import asyncio
import re
from decimal import Decimal
from datetime import datetime
from typing import Protocol
from .core import Level
from ..metascalp_levels import PREFIX,signature,owned_id,parse_rows,publication_decision,crossed_owned_ids

class LevelTerminal(Protocol):
    async def levels(self,connection:int,ticker:str):...
    async def add_level(self,connection:int,ticker:str,price:str,rule:str,note:str):...
    async def remove_level(self,connection:int,level_id:int):...

def identity(connection,symbol):
    if type(connection) is not int or not 0<connection<2**31 or type(symbol) is not str or re.fullmatch('[A-Z0-9]{2,30}',symbol) is None:
        raise ValueError('invalid terminal instrument')

def _rows(response):
    rows=parse_rows(response)
    if len(rows)>4096:raise ValueError('terminal row limit')
    owned={};ids=set()
    for row in rows:
        if not isinstance(row,dict):raise ValueError('invalid terminal row')
        for lower,upper in (('id','Id'),('note','Note'),('price','Price')):
            if lower in row and upper in row and (type(row[lower]) is not type(row[upper]) or row[lower]!=row[upper]):
                raise ValueError('ambiguous terminal field')
        note=row.get('note') or row.get('Note') or ''
        if not isinstance(note,str):raise ValueError('invalid terminal note')
        value=row.get('id',row.get('Id'))
        if type(value) is not int and not (type(value) is str and re.fullmatch('[1-9][0-9]{0,9}',value)):
            raise ValueError('invalid owned terminal ID')
        numeric_id=int(value)
        if not 0<numeric_id<2**31 or numeric_id in ids:raise ValueError('ambiguous terminal ID')
        ids.add(numeric_id)
        if not note.startswith(PREFIX):continue
        ident=owned_id(row)
        if ident is None or re.fullmatch(re.escape(PREFIX)+'[a-f0-9]{24}',note) is None or note in owned:
            raise ValueError('ambiguous owned terminal row')
        raw=row.get('price',row.get('Price'))
        if type(raw) not in (str,int,float,Decimal) or len(str(raw))>256:raise ValueError('invalid owned price')
        try:price=Decimal(str(raw))
        except Exception as exc:raise ValueError('invalid owned price') from exc
        if not price.is_finite() or price<=0:raise ValueError('invalid owned price')
        owned[note]=(ident,row)
    return owned

class LevelSync:
    def __init__(self,terminal:LevelTerminal):self.terminal=terminal;self._locks={}
    def _lock(self,connection,symbol):
        identity(connection,symbol);key=(connection,symbol)
        if key not in self._locks:
            if len(self._locks)>=128:raise ValueError('terminal instrument limit')
            self._locks[key]=asyncio.Lock()
        return self._locks[key]
    async def replace(self,connection,symbol,report,*,connection_verified=False,instrument_verified=False):
        decision=publication_decision(report,connection_verified=connection_verified,instrument_verified=instrument_verified)
        if not decision.allowed:raise ValueError(decision.reason)
        wanted={}
        for level in report.levels:
            if (not isinstance(level,Level) or level.kind not in ('high','low') or type(level.timeframe) is not str or not 1<=len(level.timeframe)<=16
                    or not 1<=len(str(level.price))<=256
                    or not isinstance(level.source_start,datetime) or level.source_start.tzinfo is None):raise ValueError('invalid level DTO')
            note=PREFIX+signature(symbol,level)
            if note in wanted:raise ValueError('duplicate desired level')
            wanted[note]=level
        async with self._lock(connection,symbol):
            existing=_rows(await self.terminal.levels(connection,symbol))
            stale=[ident for note,(ident,_) in existing.items() if note not in wanted]
            additions=[(note,level) for note,level in wanted.items() if note not in existing]
            for ident in stale:await self.terminal.remove_level(connection,ident)
            for note,level in additions:
                rule='GreaterThanEqual' if level.kind=='high' else 'LessThanEqual'
                await self.terminal.add_level(connection,symbol,str(level.price),rule,note)
            return len(wanted)
    async def crossed(self,connection,symbol,previous,current,*,contiguous=False,source=None):
        if type(contiguous) is not bool:raise ValueError('literal continuity required')
        if not contiguous or source!='exchange_execution':return 0
        if any(not isinstance(x,Decimal) or not x.is_finite() or x<=0 for x in (previous,current)):raise ValueError('invalid observed prices')
        async with self._lock(connection,symbol):
            owned=_rows(await self.terminal.levels(connection,symbol))
            rows=[row for _,row in owned.values()]
            selected=crossed_owned_ids(rows,previous,current,contiguous=True,source=source)
            for ident in selected:await self.terminal.remove_level(connection,ident)
            return len(selected)

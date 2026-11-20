"""Typed client for the external MetaScalp localhost annotation protocol.

Ported from Meta Analyse PR82 ports.py. Client creation is explicitly caller-
owned: inject a managed asynchronous HTTP adapter with ambient proxies disabled.
No network runs at import/construction. Discovery locates an untrusted candidate,
never establishes publication/connection/instrument authorization.
"""
from __future__ import annotations
import asyncio
import re
from decimal import Decimal,InvalidOperation
from typing import Protocol,Any,Awaitable,Callable

class TerminalResponse(Protocol):
    status_code:int
    content:bytes
    def json(self)->Any:...
class TerminalHttpClient(Protocol):
    async def request(self,method:str,url:str,*,timeout:float,follow_redirects:bool,**kwargs)->TerminalResponse:...
    async def aclose(self)->None:...
class TerminalTransportError(ConnectionError):pass

def _id(value):
    if type(value) is not int or not 0<value<2**31:raise ValueError('invalid terminal ID')
def _ticker(value):
    if type(value) is not str or re.fullmatch('[A-Z0-9]{2,30}',value) is None:raise ValueError('invalid terminal ticker')

class TerminalClient:
    def __init__(self,client:TerminalHttpClient,*,sleep:Callable[[float],Awaitable[None]]=asyncio.sleep):
        self.client=client;self._base=None;self._discovery=asyncio.Lock();self._sleep=sleep
    @property
    def base(self):return self._base
    def _decode(self,response):
        if type(response.status_code) is not int or not 200<=response.status_code<300:raise TerminalTransportError('terminal HTTP status rejected')
        if type(response.content) is not bytes or len(response.content)>1048576:raise ValueError('terminal response budget')
        return response.json() if response.content else None
    async def discover(self)->str:
        async with self._discovery:
            if self._base is not None:return self._base
            for port in range(17845,17856):
                root=f'http://127.0.0.1:{port}'
                try:
                    response=await self.client.request('GET',root+'/ping',timeout=3,follow_redirects=False)
                    data=self._decode(response)
                    # Preserve vendor discovery heuristic only as a locator.
                    if isinstance(data,dict) and 'meta' in str(data).lower():
                        self._base=root;return root
                except (OSError,TimeoutError,ValueError):continue
            raise ConnectionError('external terminal not found on localhost ports17845..17855')
    async def _request(self,method,endpoint,**kwargs):
        root=self._base or await self.discover()
        attempts=3 if method=='GET' else 1
        for attempt in range(attempts):
            try:
                response=await self.client.request(method,root+endpoint,timeout=3,follow_redirects=False,**kwargs)
                return self._decode(response)
            except (OSError,TimeoutError):
                if attempt==attempts-1:
                    self._base=None;raise
                await self._sleep(.25*2**attempt)
    async def connections(self):return await self._request('GET','/api/connections')
    async def open_combos(self,symbols:list[str]):
        if type(symbols) is not list or not 1<=len(symbols)<=20:raise ValueError('select1to20tickers')
        for symbol in symbols:_ticker(symbol)
        if len(set(symbols))!=len(symbols):raise ValueError('duplicate terminal ticker')
        return await self._request('POST','/api/combo',json={'tickers':symbols.copy(),'activate':True})
    async def levels(self,connection:int,ticker:str):
        _id(connection);_ticker(ticker)
        return await self._request('GET',f'/api/connections/{connection}/user-levels',params={'Ticker':ticker})
    async def add_level(self,connection:int,ticker:str,price:str,rule:str,note:str):
        _id(connection);_ticker(ticker)
        if type(price) is not str or not 1<=len(price)<=256:raise ValueError('invalid terminal price')
        try:value=Decimal(price)
        except InvalidOperation as exc:raise ValueError('invalid terminal price') from exc
        if not value.is_finite() or value<=0:raise ValueError('invalid terminal price')
        if type(rule) is not str or rule not in ('LessThanEqual','GreaterThanEqual'):raise ValueError('invalid terminal level direction')
        if type(note) is not str or re.fullmatch('terminan:[a-f0-9]{24}',note) is None:raise ValueError('invalid terminal owner note')
        # The vendor protocol currently has no direction field; preserve that
        # wire shape rather than invent an unsupported broker/order parameter.
        return await self._request('POST',f'/api/connections/{connection}/user-levels',json={'ticker':ticker,'price':price,'name':'Terminan','note':note,'lineStyle':'Dashed','lineThickness':1,'lineColor':'#E0AA44'})
    async def remove_level(self,connection:int,level_id:int):
        _id(connection);_id(level_id)
        return await self._request('DELETE',f'/api/connections/{connection}/user-levels/{level_id}')
    async def close(self):await self.client.aclose()

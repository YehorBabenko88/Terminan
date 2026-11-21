"""Canonical read-only research presenter; no collectors, native helpers or DB writers."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from decimal import Decimal
from market_math import exact_sum
from .paper import PaperEngine
from .analytics.flow_bridge import FlowBridge
from .analytics.orderflow_adapters import from_records
from .analytics.orderflow_aggregation import aggregate_by_time
from .analytics.orderflow_view import make_rows
from .migration.historical_trades import FlowHistorySnapshot,to_orderflow_records

@dataclass(frozen=True)
class ResearchSnapshot:
    symbols: tuple=()
    stats: tuple=()
    flow_rows: tuple=()
    flow_state: str='disconnected'
    flow_status: str='No qualified market-data stream attached'
    status: str='Read-only research; no exchange orders'
    market_events: tuple=()
    market_gaps: tuple=()
    market_ages: tuple=()
    overview: tuple=()
    readiness: tuple=()
    orderflow_rows: tuple=()
    orderflow_status: str='No historical snapshot selected'
    flow_history: object=None
    flow_history_request_id: int=0

class ResearchService:
    def __init__(self,publish,*,source=None,journal=None,terminal_client=None):
        self.publish,self.source,self.journal=publish,source,journal
        self.terminal_client=terminal_client
        self.engine=journal.engine if journal is not None else PaperEngine()
        self.bridge=FlowBridge();self.symbols=();self.closing=False
        self.status='Read-only research; no exchange orders'
        self.flow_state='disconnected';self.flow_status='No qualified market-data stream attached'
        self.flow_history=None;self._history_generation=0;self.orderflow_rows=()
        self.orderflow_status='No historical snapshot selected';self.readiness={}
    def initialize(self):
        # Source/client dependencies are explicit reviewed injections. Nothing
        # starts an exchange connection or adopts a source database at import.
        return None
    async def refresh(self):
        if self.source is None:
            self.status='Market-data catalogue unavailable';return
        self.symbols=tuple(await self.source.instruments())
    async def open_selected(self,symbols):
        if self.terminal_client is None:raise RuntimeError('TERMINAL_CLIENT_NOT_CONFIGURED')
        await self.terminal_client.open_combos(tuple(symbols))
    async def locate_metascalp(self):
        if self.terminal_client is None:
            self.status='External terminal connector not configured';return
        await self.terminal_client.discover()
    async def start_monitor(self):
        self.status='Monitoring requires the authenticated Unified read-only status source'
    def connect_flow(self,symbols,level):
        # No live source adapter is silently reconstructed from old collectors.
        self.flow_state='failed';self.flow_status='Qualified market-data stream adapter required'
    async def disconnect_flow(self):
        self.bridge.invalidate(self.symbols);self.flow_state='disconnected'
        self.flow_status='Disconnected; continuity remains unverified'
    async def load_flow_history(self,*,symbol,start,end,limit=5000):
        self._history_generation+=1;request_id=self._history_generation
        self.flow_history=None
        if self.source is None:
            self.status='Flow History unavailable: source not configured';return
        snapshot=await self.source.history_snapshot(symbol=symbol,start=start,end=end,limit=limit)
        if not isinstance(snapshot,FlowHistorySnapshot):raise ValueError('INVALID_HISTORY_SNAPSHOT')
        if request_id!=self._history_generation or self.closing:return
        self.flow_history=snapshot
        self.load_orderflow_records(to_orderflow_records(snapshot))
    def load_orderflow_records(self,records,interval_ms=60000):
        grouped=aggregate_by_time(from_records(records),interval_ms)
        self.orderflow_rows=make_rows(grouped,quality='UNVERIFIED')
        self.orderflow_status='Historical snapshot; authenticity and coverage unverified'
    async def configure_paper(self,enabled=None,rules=None):
        if enabled:
            raise RuntimeError('QUALIFIED_SOURCE_AND_DURABLE_PAPER_ADMISSION_REQUIRED')
        if enabled is False:self.engine.enabled=False
        if rules:
            allowed={'threshold','stop_pct','fee_rate'}
            if set(rules)-allowed or self.engine.positions:raise ValueError('PAPER_RULE_UPDATE_REFUSED')
            values={name:getattr(self.engine,name) for name in allowed}
            values.update({name:Decimal(str(value)) for name,value in rules.items()})
            candidate=PaperEngine(notional=self.engine.notional,slippage_bps=self.engine.slippage_bps,**values)
            for name in allowed:setattr(self.engine,name,getattr(candidate,name))
    def set_readiness(self,symbol,progress):self.readiness[symbol]=progress
    def snapshot(self):
        stats=[]
        for symbol in sorted(set(self.symbols)|{fill.symbol for fill in self.engine.fills}):
            fills=[fill for fill in self.engine.fills if fill.symbol==symbol]
            stats.append((symbol,str(len(fills)),str(sum(fill.net>0 for fill in fills)),
                str(exact_sum(fill.net for fill in fills)),self.engine.positions[symbol].side if symbol in self.engine.positions else '-'))
        return ResearchSnapshot(symbols=self.symbols,stats=tuple(stats),flow_rows=self.bridge.snapshot(),
            flow_state=self.flow_state,flow_status=self.flow_status,status=self.status,
            readiness=tuple(sorted(self.readiness.items())),orderflow_rows=self.orderflow_rows,
            orderflow_status=self.orderflow_status,flow_history=self.flow_history,
            flow_history_request_id=self._history_generation)
    async def publish_loop(self):
        while not self.closing:
            self.publish(self.snapshot());await asyncio.sleep(.1)
    async def close(self):
        self.closing=True;self._history_generation+=1
        await self.disconnect_flow()

"""Canonical research strategy discovery; no loader, scheduler or execution grant.

Availability means a pure research generator exists. Signal validation and the
single PaperEngine's simulation admission remain separate caller obligations.
Discovery creates detached immutable descriptors and never calls a generator.
"""
from dataclasses import dataclass,field
from enum import Enum
from types import FunctionType
from .strategy_entries import (generate_sweep_reclaim_entries,
    generate_breakout_retest_entries,generate_profile_reclaim_entries)
from .continuation_strategy import generate_continuation_signals

class StrategyAvailability(str,Enum):
    SPECIFICATION_ONLY='SPECIFICATION_ONLY'
    RESEARCH_GENERATOR='RESEARCH_GENERATOR'
class ResearchInput(str,Enum):
    UNSUPPORTED='UNSUPPORTED'
    OHLC_STRUCTURE='OHLC_STRUCTURE'
    OHLC_STRUCTURE_VOLATILITY='OHLC_STRUCTURE_VOLATILITY'
    BODY_VOLATILITY='BODY_VOLATILITY'
    OHLC_PROFILE_FLOW='OHLC_PROFILE_OPTIONAL_FLOW'
class ResearchOutput(str,Enum):
    NONE='NONE'
    SIGNALS='RESEARCH_SIGNALS'
    ENTRIES='RESEARCH_ENTRIES'
@dataclass(frozen=True,slots=True)
class ResearchStrategy:
    id:str
    version:str
    setup:str
    confirmations:tuple[str,...]
    direction:str|None
    entry_rule:str|None
    required_features:tuple[str,...]
    generator:FunctionType|None
    inputs:ResearchInput
    output:ResearchOutput
    @property
    def availability(self):
        return StrategyAvailability.SPECIFICATION_ONLY if self.generator is None else StrategyAvailability.RESEARCH_GENERATOR
    source_authentication:str=field(default='NOT_EVALUATED',init=False)
    execution_authority:bool=field(default=False,init=False)
    trading_authorized:bool=field(default=False,init=False)

def research_strategy_catalog():
    """Eight distinct research specifications, four with canonical generators.

    Input and output contracts are explicit: continuation emits ResearchSignal,
    while the other implemented strategies emit ResearchEntry with evidence.
    No old import path, executable-status alias or dynamic adapter is retained.
    """
    def spec(identity,setup,confirmations=(),direction=None,entry=None,requires=(),generator=None,
             inputs=ResearchInput.UNSUPPORTED,output=ResearchOutput.NONE):
        return ResearchStrategy(identity,'1',setup,confirmations,direction,entry,requires,generator,inputs,output)
    return (
        spec('level_impulse','level_impulse',requires=('level','volatility','volume_expansion')),
        spec('level_impulse_delta','level_impulse',('volume_expansion','delta'),requires=('level','public_trade_aggregates')),
        spec('sweep_reclaim','liquidity_sweep',('return_inside',),entry='reclaim',requires=('ohlc','liquidity_sweep'),
             generator=generate_sweep_reclaim_entries,inputs=ResearchInput.OHLC_STRUCTURE,output=ResearchOutput.ENTRIES),
        spec('failed_breakout','failed_breakout',direction='reversal',entry='return_inside_level'),
        spec('breakout_retest','breakout_retest',('volume_expansion',),'continuation',requires=('ohlc','bos','volatility'),
             generator=generate_breakout_retest_entries,inputs=ResearchInput.OHLC_STRUCTURE_VOLATILITY,output=ResearchOutput.ENTRIES),
        spec('volatility_continuation','compression_expansion',('volume_expansion',),'continuation',requires=('candle_body','volatility'),
             generator=generate_continuation_signals,inputs=ResearchInput.BODY_VOLATILITY,output=ResearchOutput.SIGNALS),
        spec('profile_reclaim','poc_reclaim',('delta',),'reversion_or_continuation',requires=('ohlc','profile'),
             generator=generate_profile_reclaim_entries,inputs=ResearchInput.OHLC_PROFILE_FLOW,output=ResearchOutput.ENTRIES),
        spec('open_interest_delta_impulse','impulse',('open_interest','delta','volume_expansion')),
    )

def research_strategy(strategy_id):
    """Resolve a literal canonical ID without importing or invoking user text."""
    if type(strategy_id) is not str:raise ValueError('RESEARCH_STRATEGY_LITERAL_ID_REQUIRED')
    for definition in research_strategy_catalog():
        if definition.id==strategy_id:return definition
    raise ValueError('RESEARCH_STRATEGY_UNKNOWN_ID')

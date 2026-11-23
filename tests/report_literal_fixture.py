"""Declared typed fixtures only; no evaluator or engine is constructed."""
from dataclasses import fields
from decimal import Decimal as D
from datetime import datetime,timezone
import types,dataclasses
from terminan import research_entry_evaluation as rich,research_evaluation as evaluation,paper
from terminan.strategy_entries import ResearchEntry,EntryEvidence,ResearchEntryPattern,EntrySide,RiskBasis
from terminan.continuation_strategy import CandleBodyObservation
from terminan.market_structure import MarketStructureReference
from terminan.volatility import VolatilityMetrics,VolatilityRegime
from terminan.research_signals import ResearchSignal,SignalExecution
from terminan.strategy_screening import ResearchPatternVerdict,ScreeningStatus
import history_statistics as numeric
def fixture(disposition):
 vol=VolatilityMetrics(0,60000,.01,.02,.03,.04,2.,3.,.8,VolatilityRegime.HIGH,'literal.qa.v1')
 projected={f.name:getattr(vol,f.name) for f in dataclasses.fields(vol)};projected['regime']=vol.regime.value
 context=types.MappingProxyType(dict(schema='terminan.entry-context.v1',decision_ms=60000,metadata=types.MappingProxyType({'pattern':'volatility_continuation_v2'}),volatility=types.MappingProxyType(projected),profile=None,source_authentication='NOT_EVALUATED',execution_authority=False,trading_authorized=False))
 signal=ResearchSignal('BTCUSDT',60000,'long','market',None,D(100),D(102));body=CandleBodyObservation(0,60000,60000,100,101)
 evidence=EntryEvidence(101,(MarketStructureReference(0,60000,60000),),None,None,2.,VolatilityRegime.HIGH,None,None,None,.01,RiskBasis.OBSERVED_ATR,body_reference=body,volatility=vol,atr_percentile=.8)
 entry=ResearchEntry(ResearchEntryPattern.CONTINUATION,60000,EntrySide.LONG,101,signal,evidence,context)
 fill=paper.PaperFill('BTCUSDT','long',D(101),D(100),'stop',D(-1),D('.1'),D('-1.1'),datetime(1970,1,1,0,1,tzinfo=timezone.utc))
 execution=SignalExecution(60000,60000,D(1),fill,'OHLC_CONSERVATIVE_NO_TICK_ORDER') if disposition is evaluation.EvaluationDisposition.FILLED else None
 outcome=evaluation.EvaluationOutcome(signal,disposition,None if disposition is evaluation.EvaluationDisposition.OUTSIDE_TEST_WINDOW else 0,None if disposition is evaluation.EvaluationDisposition.OUTSIDE_TEST_WINDOW else (120000 if disposition is evaluation.EvaluationDisposition.FILLED else 180000),execution)
 pnl=numeric.NumericProfitLossSummary(numeric.NumericSampleSummary(1,0,1,-1.1,-1.1,0.),0.,1.1,numeric.ProfitFactorObservation('FINITE',0.),1.1,1)
 if disposition is not evaluation.EvaluationDisposition.FILLED:pnl=numeric.NumericProfitLossSummary(numeric.NumericSampleSummary(0,0,0,0.,0.,0.),0.,0.,numeric.ProfitFactorObservation('FINITE',0.),0.,0)
 fold=evaluation.EvaluationFold(0,0,180000,0,pnl);verdict=ResearchPatternVerdict('volatility_continuation_v2',ScreeningStatus.REJECT,numeric.NumericFoldSummary(1,pnl.numeric.count,0,int(disposition is evaluation.EvaluationDisposition.FILLED),pnl.numeric.mean,0.,1,0,0),('DECLARED_LITERAL_QA',))
 dataset=evaluation.EvaluationDataset('a'*64,'BTCUSDT','USDT',0,180000);owner=evaluation.ResearchEvaluation('b'*64,dataset,(fold,),(outcome,),pnl,None,verdict)
 return rich.ResearchEntryEvaluation('c'*64,(entry,),owner,(rich.EntryEvaluationOutcome(entry,outcome),))
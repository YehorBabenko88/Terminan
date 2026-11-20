"""Frozen original execution/sizing results; no retired package or engine imported."""
import unittest,json,dataclasses
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from pathlib import Path
from terminan.paper import PaperEngine,ClosedMinute,ExecutionTrade,apply_sizing,ruin_stats

def encode(value):
    if isinstance(value,Decimal):return str(value)
    if isinstance(value,datetime):return value.isoformat()
    if dataclasses.is_dataclass(value):return encode(dataclasses.asdict(value))
    if isinstance(value,dict):return {k:encode(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [encode(v) for v in value]
    return value

class HistoricalPaperVectorsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vectors=json.loads((Path(__file__).parent/'fixtures/canonical-paper-vectors.json').read_text())
    def test_original_engine_event_states_match_canonical_engine(self):
        stamp=datetime(2026,10,15,12,tzinfo=timezone.utc)
        for case in self.vectors['cases']:
            with self.subTest(case=case['name']):
                engine=PaperEngine();engine.enabled=True
                engine.on_closed_minute('BTCUSDT',ClosedMinute(stamp,Decimal('100'),case['complete']))
                for event,want in zip(case['events'],case['states'],strict=True):
                    seconds,price=event
                    engine.on_trade(ExecutionTrade('BTCUSDT',stamp+timedelta(seconds=seconds),Decimal(price)))
                    self.assertEqual(encode(dict(reference=engine.reference,positions=engine.positions,fills=engine.fills)),want)
    def test_all_original_sizing_modes_and_caps_match_frozen_rows(self):
        for case in self.vectors['sizing']:
            with self.subTest(options=case['options']):
                self.assertEqual(apply_sizing(self.vectors['sizing_rows'],**case['options']),case['result'])
    def test_original_ruin_scenarios_match_frozen_rows(self):
        for case in self.vectors['ruin']:
            with self.subTest(options=case['options']):
                self.assertEqual(ruin_stats(self.vectors['sizing_rows'],**case['options']),case['result'])

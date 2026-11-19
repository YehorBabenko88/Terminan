import unittest
from terminan.contracts import TradeEvent, align_trades, aggregate_footprint, poc_close_events

class ContractTests(unittest.TestCase):
    def test_trade_validation(self):
        base=dict(run_id='r',strategy_id='s',symbol='BTCUSDT',trade_id='t',entry_ms=100,exit_ms=200,entry_price=10,exit_price=12,side='long',quantity=2,pnl=4)
        t=TradeEvent.parse(base)
        self.assertEqual(align_trades([t],150,160),[t])
        with self.assertRaises(ValueError):TradeEvent.parse({**base,'exit_ms':99})
        with self.assertRaises(ValueError):TradeEvent.parse({**base,'side':'other'})
    def test_poc_tie_and_close(self):
        rows=[dict(t=100,price=11,volume=5),dict(t=100,price=10,volume=5),dict(t=200,price=9,volume=8)]
        buckets=aggregate_footprint(rows)
        self.assertEqual(buckets[0]['poc'],10)
        events=poc_close_events(buckets,[dict(t=100,c=11),dict(t=200,c=9)])
        self.assertEqual([e['relation'] for e in events],['above','at'])
    def test_no_negative_volume(self):
        with self.assertRaises(ValueError):aggregate_footprint([dict(t=1,price=2,volume=-1)])

class StrategyMigrationTests(unittest.TestCase):
    """Preserve Strattester registry/spec behavior without starting a worker."""

    @staticmethod
    def definition(version='1'):
        from terminan.contracts import StrategyDefinition, DataRequirement
        class NoOp:
            pass
        return StrategyDefinition(
            'example', version, (DataRequirement('candles', ('1m',)),), NoOp,
        )

    def test_duplicate_registration_and_fingerprint_stability(self):
        from terminan.contracts import StrategyRegistry, strategy_fingerprint
        registry = StrategyRegistry()
        registry.register(self.definition())
        with self.assertRaises(ValueError):
            registry.register(self.definition())
        initial = strategy_fingerprint(registry.discover()[0])
        registry.set_enabled('example', '1', False)
        self.assertEqual(initial, strategy_fingerprint(registry.discover()[0]))
        self.assertFalse(registry.discover()[0].enabled)
        self.assertNotEqual(initial, strategy_fingerprint(self.definition('2')))

    def test_invalid_dataset_fails_closed(self):
        from terminan.contracts import DataRequirement
        with self.assertRaises(ValueError):
            DataRequirement('future_unknown_data')
        self.assertEqual(DataRequirement('open_interest').dataset, 'open_interest')

    def test_spec_only_never_becomes_executable(self):
        from terminan.contracts import HypothesisSpec, executable_hypotheses
        planned = HypothesisSpec('poc', 'poc', {'setup': 'retest'})
        executable = HypothesisSpec(
            'explicit', 'levels', {}, execution_status='EXECUTABLE',
            signal_generator='reviewed-v1',
        )
        self.assertEqual(executable_hypotheses([planned, executable]), (executable,))
        with self.assertRaises(ValueError):
            HypothesisSpec('unsafe', 'levels', {}, execution_status='EXECUTABLE')

if __name__=='__main__':unittest.main()

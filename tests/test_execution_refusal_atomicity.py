"""Atomic malformed execution refusal; pure state/Math, no network or process I/O."""
from copy import deepcopy
from decimal import Decimal as D
from types import SimpleNamespace
import unittest
from terminan.analytics.tape_velocity import TapeVelocity
from terminan.analytics.footprint import Footprint,FootprintCell


def execution(**changes):
    values=dict(symbol='BTCUSDT',timestamp_ms=100,price=D('100'),quantity=D('1'),taker_side='Buy')
    values.update(changes)
    return SimpleNamespace(**values)


class ExecutionRefusalAtomicity(unittest.TestCase):
    def test_tape_invalid_execution_retains_complete_window_even_on_gap(self):
        for changes in ({'quantity':D('NaN')},{'quantity':D('-1')},{'quantity':D('1e1001')},
                        {'price':D('Infinity')},{'taker_side':'bad'},{'timestamp_ms':True}):
            for contiguous in (True,False):
                with self.subTest(changes=changes,contiguous=contiguous):
                    tape=TapeVelocity(D('1'))
                    tape.add(execution(),D('100'),contiguous=True)
                    before=deepcopy((tape.events,tape.last_ms))
                    with self.assertRaises(ValueError):
                        tape.add(execution(**changes),D('100'),contiguous=contiguous)
                    self.assertEqual((tape.events,tape.last_ms),before)

    def test_contiguous_requires_literal_bool_before_any_state_change(self):
        for bad in ('false','true',1,0,None,[],object()):
            for kind in ('tape','footprint'):
                with self.subTest(bad=repr(bad),kind=kind):
                    obj=TapeVelocity(D('1')) if kind=='tape' else Footprint('BTCUSDT',0,60000,D('1'))
                    before=deepcopy(obj.__dict__)
                    with self.assertRaises(ValueError):
                        if kind=='tape':obj.add(execution(),D('100'),contiguous=bad)
                        else:obj.add(execution(),contiguous=bad)
                    self.assertEqual(obj.__dict__,before)

    def test_invalid_constructor_quality_clock_and_numeric_settings_refuse(self):
        for options in ({'tick_size':D('NaN')},{'tick_size':D('0')},{'tick_size':D('1'),'window_ms':True},
                        {'tick_size':D('1'),'proximity_ticks':True},{'tick_size':D('1'),'proximity_ticks':D('NaN')}):
            with self.subTest(options=options),self.assertRaises(ValueError):TapeVelocity(**options)
        for options in ({'trusted':'false'},{'start_ms':True},{'interval_ms':False},{'tick_size':D('NaN')},
                        {'cells':{D('100'):FootprintCell(D('NaN'),D('0'),0)}}):
            args=dict(symbol='BTCUSDT',start_ms=0,interval_ms=60000,tick_size=D('1'));args.update(options)
            with self.subTest(options=options),self.assertRaises(ValueError):Footprint(**args)

    def test_valid_gap_and_regression_reset_but_malformed_regression_does_not(self):
        tape=TapeVelocity(D('1'));tape.add(execution(),D('100'),contiguous=True)
        before=deepcopy((tape.events,tape.last_ms))
        with self.assertRaises(ValueError):tape.add(execution(timestamp_ms=99,quantity=D('NaN')),D('100'),contiguous=True)
        self.assertEqual((tape.events,tape.last_ms),before)
        result=tape.add(execution(timestamp_ms=99),D('100'),contiguous=True)
        self.assertFalse(result.trusted);self.assertEqual(len(tape.events),0);self.assertIsNone(tape.last_ms)
        tape.add(execution(),D('100'),contiguous=True)
        self.assertFalse(tape.add(execution(timestamp_ms=101),D('100'),contiguous=False).trusted)
        self.assertEqual(len(tape.events),0)

    def test_exact_boundary_does_not_use_rounded_display_to_grant_trust(self):
        tape=TapeVelocity(D('0.001'),proximity_ticks=9)
        result=tape.add(execution(price=D('1.00900000000000000000000000000000000000000001')),D('1'),contiguous=True)
        self.assertEqual(result.distance_ticks,D('9'));self.assertFalse(result.trusted)

    def test_footprint_bad_quantity_preserves_existing_cell_and_quality(self):
        fp=Footprint('BTCUSDT',0,60000,D('1'));fp.add(execution(),contiguous=True)
        before=deepcopy(fp)
        with self.assertRaises(ValueError):fp.add(execution(quantity=D('NaN')),contiguous=False)
        self.assertEqual(fp,before)
        fp.add(execution(timestamp_ms=101),contiguous=False)
        self.assertFalse(fp.trusted);self.assertEqual(fp.cells[D('100')].count,2)

if __name__=='__main__':unittest.main()

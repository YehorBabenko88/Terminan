"""Public presenter configuration against the sole actual PaperEngine; no event loop."""
import copy
import unittest
from decimal import Decimal
from types import SimpleNamespace
from terminan.paper import PaperEngine
from terminan.research_service import ResearchService

def complete(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as done:
        return done.value
    finally:
        coroutine.close()
    raise AssertionError('configuration unexpectedly awaits external work')

class PaperRuleConfigurationTests(unittest.TestCase):
    def service(self):
        engine=PaperEngine(notional=Decimal('123'),slippage_bps=Decimal('7.5'))
        published=[]
        service=ResearchService(published.append,journal=SimpleNamespace(engine=engine))
        return service,engine,published

    def test_valid_rules_preserve_engine_and_existing_basis_points(self):
        service,engine,published=self.service()
        before_id=id(engine);engine.enabled=True
        engine.reference['BTCUSDT']=('retained','reference')
        engine.last_trade_time['BTCUSDT']='retained-time'
        complete(service.configure_paper(rules={'threshold':'0.02','stop_pct':'0.01','fee_rate':'0.001'}))
        self.assertEqual((engine.threshold,engine.stop_pct,engine.fee_rate),(Decimal('0.02'),Decimal('0.01'),Decimal('0.001')))
        self.assertEqual((engine.notional,engine.slippage_bps),(Decimal('123'),Decimal('7.5')))
        self.assertEqual(id(service.engine),before_id);self.assertTrue(engine.enabled)
        self.assertEqual(engine.reference,{'BTCUSDT':('retained','reference')})
        self.assertEqual(engine.last_trade_time,{'BTCUSDT':'retained-time'})
        self.assertEqual(engine.positions,{});self.assertEqual(engine.fills,[]);self.assertEqual(published,[])

    def test_partial_rule_update_keeps_unmodified_policy(self):
        service,engine,_=self.service();old=(engine.stop_pct,engine.fee_rate)
        complete(service.configure_paper(rules={'threshold':'0.03'}))
        self.assertEqual(engine.threshold,Decimal('0.03'))
        self.assertEqual((engine.stop_pct,engine.fee_rate),old);self.assertEqual(engine.slippage_bps,Decimal('7.5'))
        self.assertFalse(engine.enabled);self.assertEqual(service.snapshot().stats,())

    def test_invalid_rules_refuse_before_any_engine_update(self):
        for rules in ({'threshold':'NaN'},{'stop_pct':'-1'},{'fee_rate':'-0.01'},{'unknown':'1'}):
            service,engine,published=self.service();before=copy.deepcopy(vars(engine))
            with self.subTest(rules=rules),self.assertRaises((ValueError,ArithmeticError)):
                complete(service.configure_paper(rules=rules))
            self.assertEqual(vars(engine),before);self.assertEqual(published,[])

    def test_open_position_blocks_rule_change_and_enable_stays_fail_closed(self):
        service,engine,_=self.service();engine.positions['BTCUSDT']='owned-position'
        before=copy.deepcopy(vars(engine))
        with self.assertRaises(ValueError):complete(service.configure_paper(rules={'threshold':'0.02'}))
        self.assertEqual(vars(engine),before)
        with self.assertRaises(RuntimeError):complete(service.configure_paper(enabled=True))
        self.assertEqual(vars(engine),before)

    def test_disable_and_empty_update_preserve_policy_and_publish_contract(self):
        service,engine,published=self.service();engine.enabled=True
        complete(service.configure_paper(enabled=False));self.assertFalse(engine.enabled)
        before=copy.deepcopy(vars(engine));complete(service.configure_paper(rules={}))
        self.assertEqual(vars(engine),before);self.assertEqual(published,[])

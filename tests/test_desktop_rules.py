"""Exercise the actual desktop method without importing Qt or starting a loop."""
import ast
import copy
import decimal
import pathlib
import unittest
from types import SimpleNamespace
from decimal import Decimal
from terminan import paper
from terminan.research_service import ResearchService

def update_method():
    source=pathlib.Path(paper.__file__).with_name('desktop.py')
    tree=ast.parse(source.read_bytes())
    owner=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ResearchWindow')
    method=next(n for n in owner.body if isinstance(n,ast.FunctionDef) and n.name=='update_rules')
    namespace={'Decimal':Decimal}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),str(source),'exec',dont_inherit=True),namespace)
    return namespace['update_rules']

class Spin:
    def __init__(self,value):self.number=value
    def value(self):return self.number

class DesktopRuleMappingTests(unittest.TestCase):
    def view(self,values=(1.5,0.5,0.06)):
        service=ResearchService(lambda value:None);scheduled=[]
        def schedule(coroutine):
            scheduled.append('configure')
            try:coroutine.send(None)
            except StopIteration:return
            finally:coroutine.close()
            raise AssertionError('unexpected external await')
        view=SimpleNamespace(service=service,schedule=schedule,threshold=Spin(values[0]),stop=Spin(values[1]),fee=Spin(values[2]))
        return view,scheduled

    def test_actual_desktop_method_updates_named_public_service_rules(self):
        view,scheduled=self.view();engine=view.service.engine;before_id=id(engine)
        update_method()(view)
        self.assertEqual((engine.threshold,engine.stop_pct,engine.fee_rate),(Decimal('0.015'),Decimal('0.005'),Decimal('0.0006')))
        self.assertEqual(scheduled,['configure']);self.assertEqual(id(view.service.engine),before_id)
        self.assertEqual(engine.slippage_bps,Decimal('2'));self.assertFalse(engine.enabled)

    def test_ui_range_boundaries_and_three_decimal_values_are_exact(self):
        for values in ((0.001,20,0.001),(20,0.001,20),(1.234,0.567,0.089)):
            view,scheduled=self.view(values);update_method()(view)
            expected={ (0.001,20,0.001):('0.00001','0.2','0.00001'),(20,0.001,20):('0.2','0.00001','0.2'),(1.234,0.567,0.089):('0.01234','0.00567','0.00089')}[values]
            self.assertEqual((view.service.engine.threshold,view.service.engine.stop_pct,view.service.engine.fee_rate),tuple(map(Decimal,expected)))
            self.assertEqual(scheduled,['configure'])

    def test_hostile_decimal_context_leaves_flags_and_policy_exact(self):
        view,scheduled=self.view((1.234,0.567,0.089));method=update_method()
        with decimal.localcontext() as c:
            c.prec=1
            for signal in c.traps:c.traps[signal]=True
            c.clear_flags();before=dict(c.flags);method(view);self.assertEqual(dict(c.flags),before)
        self.assertEqual(view.service.engine.threshold,Decimal('0.01234'));self.assertEqual(scheduled,['configure'])

    def test_missing_controls_and_bad_input_do_not_schedule_or_mutate(self):
        view,scheduled=self.view();del view.fee;update_method()(view);self.assertEqual(scheduled,[])
        for bad in ('NaN','Infinity','bad'):
            view,scheduled=self.view((1.5,0.5,bad));before=copy.deepcopy(vars(view.service.engine))
            with self.subTest(bad=bad),self.assertRaises((ValueError,ArithmeticError)):update_method()(view)
            self.assertEqual(vars(view.service.engine),before);self.assertEqual(scheduled,[])

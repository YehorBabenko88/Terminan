"""Canonical research import validation only; no Data runtime, DB, listener or source grant."""
import copy
import importlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from hashlib import sha256
from decimal import Decimal
from terminan.paper_ledger import canonical_json
FIXTURE=Path(__file__).parent/'fixtures/research-import/original-export.synthetic.json'

def seal(value):
    value['completion_receipt']=sha256(canonical_json({k:v for k,v in value.items() if k!='completion_receipt'})).hexdigest()
    return value
def trust(value):return {(value['producer_identity'],value['source_revision'],value['run_id'],value['completion_receipt'])}
def record():
    value=json.loads(FIXTURE.read_bytes());value['producer']='terminan';return seal(value)

class ResearchImportTests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('terminan.research_import'),'Terminan must own the research validator')
        return importlib.import_module('terminan.research_import').validate_research_import
    def deny(self,value,sources=None):
        result=self.api()(value,trust(value) if sources is None else sources)
        self.assertEqual(result['status'],'UNAVAILABLE')
        for key in ('execution_authority','trading_authorized','source_capability'):self.assertIs(result[key],False)
    def test_frozen_export_byte_identity_and_canonical_producer_without_grants(self):
        before=FIXTURE.read_bytes();self.assertEqual(sha256(before).hexdigest(),'70a0ed567ca82cb5273911c59611248c4e45a382a9f6c35e60cdab5d7f1793a3')
        legacy=json.loads(before);self.assertEqual(seal(copy.deepcopy(legacy))['completion_receipt'],legacy['completion_receipt'])
        self.deny(legacy);value=record();original=copy.deepcopy(value);out=self.api()(value,trust(value))
        self.assertEqual(out['status'],'ACCEPTED_HISTORICAL');self.assertEqual(out['run_id'],value['run_id'])
        self.assertEqual(out['completion_receipt'],value['completion_receipt']);self.assertEqual(value,original);self.assertEqual(FIXTURE.read_bytes(),before)
        for key in ('execution_authority','trading_authorized','source_capability'):self.assertIs(out[key],False)
        self.assertEqual(out['source_authenticity'],'NOT_EVALUATED');self.assertEqual(out['native'],'NOT_RUN')
    def test_external_four_tuple_is_required_and_never_self_attested(self):
        value=record();self.assertEqual(self.api()(value,set())['reason'],'SOURCE_IDENTITY_UNATTESTED')
        pin=next(iter(trust(value)))
        for sources in ((pin,),[pin],frozenset((pin,))):self.assertEqual(self.api()(value,sources)['status'],'ACCEPTED_HISTORICAL')
        for index,replacement in enumerate(('other-owner','b'*40,'11111111-1111-4111-8111-111111111111','0'*64)):
            item=list(next(iter(trust(value))));item[index]=replacement;self.deny(value,{tuple(item)})
    def test_original_adversarial_variants_refuse(self):
        changes=(lambda x:x.update(completion_receipt='0'*64),lambda x:x.update(api_version={'major':2,'minor':0}),lambda x:x.update(completed_at_ms=True),lambda x:x['dataset'].update(missing_data=[1]))
        for change in changes:
            value=record();change(value)
            with self.subTest(change=change):self.deny(value)
    def test_rehashed_forgery_cannot_reuse_original_trust(self):
        value=record();sources=trust(value);value['metrics']={'forged':True};seal(value);self.deny(value,sources)
    def test_literal_false_authority_and_version_fields(self):
        for key,values in (('execution_authority',(True,0,None)),('producer',('strattester','grid','meta_analyse')),('mode',('LIVE','PAPER'))):
            for bad in values:
                value=record();value[key]=bad;seal(value)
                with self.subTest(key=key,bad=bad):self.deny(value)
        value=record();value['api_version']['major']=True;seal(value);self.deny(value)
    def test_incomplete_dataset_or_time_order_refuses(self):
        for change in (lambda x:x['dataset'].update(coverage='PARTIAL'),lambda x:x['dataset'].update(start_ms=True),lambda x:x['dataset'].update(end_ms=-1),lambda x:x.update(completed_at_ms=59999)):
            value=record();change(value);seal(value);self.deny(value)
    def test_cost_shape_delegates_actual_math_and_refuses_invalid_numbers(self):
        for bad in (True,-1,-0.1,float('nan'),float('inf'),'0',Decimal('0'),2**1024):
            value=record();value['execution_assumptions']['fees']=bad
            if type(bad) in (bool,int,str) or type(bad) is float and bad==bad and abs(bad)!=float('inf'):seal(value)
            self.deny(value)
        import market_math
        value=record();value['execution_assumptions'].update(fees=1.25,slippage=-0.0);seal(value)
        self.assertEqual(self.api()(value,trust(value))['status'],'ACCEPTED_HISTORICAL')
        with patch.object(market_math,'finite_nonnegative_number_valid',return_value=False):self.deny(value)
        with patch.object(market_math,'finite_nonnegative_number_valid',None):self.deny(value)
    def test_optional_snapshot_and_nested_datasets_preserved(self):
        value=record();self.assertIn('input_snapshot',value);self.assertIn('datasets',value['dataset']);self.assertEqual(self.api()(value,trust(value))['status'],'ACCEPTED_HISTORICAL')
        del value['input_snapshot'];seal(value);self.assertEqual(self.api()(value,trust(value))['status'],'ACCEPTED_HISTORICAL')
    def test_opaque_metrics_are_not_claimed_as_recomputed_research_truth(self):
        value=record();value['metrics']={'declared_only':-12.5};seal(value);out=self.api()(value,trust(value))
        self.assertEqual(out['status'],'ACCEPTED_HISTORICAL');self.assertEqual(out['validation_scope'],'STRUCTURE_RECEIPT_EXTERNAL_PIN_NOT_RESEARCH_ORACLE')
    def test_hostile_containers_and_overbound_map_refuse_before_encoding(self):
        class Hostile(dict):
            def items(self):raise AssertionError('HOSTILE_CALLBACK')
            def __iter__(self):raise AssertionError('HOSTILE_CALLBACK')
        self.deny(Hostile(record()),set())
        class HostileMeta(type):
            def __eq__(self,other):raise AssertionError('METACLASS_EQUALITY_CALLBACK')
        class HostileValue(metaclass=HostileMeta):pass
        hostile=record();hostile['metrics']['object']=HostileValue();self.deny(hostile)
        huge={str(i):0 for i in range(100000)}
        module=importlib.import_module('terminan.research_import') if importlib.util.find_spec('terminan.research_import') else None
        self.assertIsNotNone(module)
        with patch.object(module,'canonical_json',side_effect=AssertionError('ENCODER_BEFORE_PREFLIGHT')):self.deny(huge,set())
        import sys
        giant=record();giant['metrics']['integer']=1<<1000000;owner=module.canonical_json
        def bounded_encoder(value):
            if type(value) is int and value.bit_length()>4096:raise AssertionError('GIANT_INT_REACHED_ENCODER')
            return owner(value)
        prior=sys.get_int_max_str_digits()
        try:
            sys.set_int_max_str_digits(0)
            with patch.object(module,'canonical_json',side_effect=bounded_encoder):self.deny(giant)
        finally:sys.set_int_max_str_digits(prior)
    def test_cycle_and_deep_shape_are_refused_without_input_mutation(self):
        value=record();value['strategy']['parameters']['cycle']=value;self.deny(value,set())
    def test_detached_record_and_trust_are_used_after_numeric_validation(self):
        import market_math
        value=record();sources=trust(value);old_run=value['run_id'];old_receipt=value['completion_receipt'];owner=market_math.finite_nonnegative_number_valid
        def mutate_original(number):
            value['run_id']='11111111-1111-4111-8111-111111111111';sources.clear();return owner(number)
        with patch.object(market_math,'finite_nonnegative_number_valid',side_effect=mutate_original):out=self.api()(value,sources)
        self.assertEqual(out['status'],'ACCEPTED_HISTORICAL');self.assertEqual((out['run_id'],out['completion_receipt']),(old_run,old_receipt))
    def test_capability_is_readonly_validation_without_new_http_route(self):
        from terminan.server import capability_snapshot
        value=capability_snapshot();self.assertIs(value['capabilities'].get('research_import_validation'),True)
        self.assertEqual(value['status'],'UNAVAILABLE');self.assertIs(value['execution_authority'],False);self.assertIs(value['trading_authorized'],False)
        self.assertIsNone(getattr(importlib.import_module('terminan.research_import'),'accept_handoff',None))

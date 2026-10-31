"""Inert producer-exported wire fixture; not numerical Math or final E2E."""
import copy
import json
from pathlib import Path
import unittest
from terminan.history_overlay import admit,canonical,digest

FIXTURE=Path(__file__).parent/'fixtures/unified-contract.v1.json'
def packet():return json.loads(FIXTURE.read_bytes())
def reseal(p):
    p['packet_sha256']=digest({k:v for k,v in p.items() if k!='packet_sha256'});return p

class UnifiedDisplayAdapterTests(unittest.TestCase):
    def test_opt_in_is_required_without_changing_active_engine_pin(self):
        with self.assertRaisesRegex(ValueError,'UNIFIED_CONTRACT_IMPORT_DISABLED'):admit(canonical(packet()))

    def test_original_clocks_values_model_and_published_oos_are_retained(self):
        p=packet();r=admit(canonical(p),allow_unified=True)
        self.assertEqual(r['qualification'],'UNQUALIFIED_CONTRACT_ONLY')
        self.assertEqual(r['identity']['market']['symbol'],'BTCUSDT')
        self.assertEqual(len(r['observations']),21);self.assertEqual(len(r['layers']),3)
        self.assertEqual(r['layers'][1]['points'][-1],{'time':1200000,'available':1200500,'value':202})
        self.assertEqual(r['layers'][1]['known_at'],1202000)
        self.assertEqual(r['diagnostics'][0]['kind'],'DESCRIPTIVE_NOT_OOS')
        self.assertEqual(r['diagnostics'][0]['values'],[0])
        self.assertEqual(r['oos']['available'],1270000)
        self.assertEqual(r['metadata']['engine']['commit'],'b'*40)
        self.assertEqual(r['scientific_proof']['request']['nodes'][0]['provenance']['sha256'],p['joint_result']['history']['prefix_digest'])

    def test_inner_request_receipt_prefix_and_source_substitutions_fail(self):
        for mutate in (lambda p:p['joint_request']['history']['rows'][0].update(close=999),
                       lambda p:p['joint_result'].update(completion_receipt='0'*64),
                       lambda p:p['joint_result']['math_source'].update(commit='0'*40),
                       lambda p:p.update(joint_published_at_ms=1200000),
                       lambda p:p.update(qualification='QUALIFIED')):
            p=packet();mutate(p)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):admit(canonical(reseal(p)),allow_unified=True)

    def test_rehashed_future_availability_and_changed_prefix_are_rejected(self):
        for field,value in [('availableAt',[2000000]*20),('timestamps',list(range(20)))]:
            p=packet();p['joint_result']['scientific']['outputs'][0][field]=value
            j=p['joint_result'];j['completion_receipt']=digest({k:v for k,v in j.items() if k!='completion_receipt'})
            with self.subTest(field=field),self.assertRaises(ValueError):admit(canonical(reseal(p)),allow_unified=True)

    def test_scalar_without_publication_or_future_oos_is_not_promoted(self):
        p=packet();p['history'].pop('oos_available_at_ms');p['history'].pop('published_at_ms')
        p['history']['handoff_sha256']=digest({k:v for k,v in p['history'].items() if k!='handoff_sha256'})
        r=admit(canonical(reseal(p)),allow_unified=True)
        self.assertIsNone(r['oos']);self.assertEqual(r['diagnostics'][0]['kind'],'DESCRIPTIVE_NOT_OOS')

    def test_self_consistent_request_still_requires_real_wire_clock_and_model_fields(self):
        for mutate in (lambda h:h.update(train_count=True),lambda h:h.update(model_version='invented'),
                       lambda h:h['rows'][0].update(source_event_end_ms=60001),
                       lambda h:h['rows'][0].update(revision='not-a-sha')):
            p=packet();h=p['joint_request']['history'];mutate(h);j=p['joint_result']
            j['provenance']={k:h[k] for k in ('dataset_id','dataset_fingerprint','source','market','units','decision_ms','rows')}
            j['request_digest']=digest(p['joint_request']);j['history']['request_digest']=digest(h);j['history']['prefix_digest']=digest(h['rows'])
            j['completion_receipt']=digest({k:v for k,v in j.items() if k!='completion_receipt'})
            history=p['history'];history['forecast_points'][1]['request_digest']=digest(h)
            history['handoff_sha256']=digest({k:v for k,v in history.items() if k!='handoff_sha256'})
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):admit(canonical(reseal(p)),allow_unified=True)

    def test_forecast_feature_clocks_cannot_disagree_with_joint_result(self):
        p=packet();h=p['history'];h['forecast_points'][1].update(feature_event_end_ms=1140000,feature_available_at_ms=1140500)
        h['handoff_sha256']=digest({k:v for k,v in h.items() if k!='handoff_sha256'})
        with self.assertRaises(ValueError):admit(canonical(reseal(p)),allow_unified=True)

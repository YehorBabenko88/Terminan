"""Admission boundaries; end-to-end fixtures are produced by the real exporter."""
import copy
import hashlib
import json
import unittest

def seal(p):
    p.pop('handoff_sha256', None)
    p['handoff_sha256'] = hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return p

def packet():
    return seal(dict(schema='terminan.history.scientific-handoff.v1',
        evidence_class='SYNTHETIC',source_authenticity='UNATTESTED',scientific_api='NOT_EXECUTED',
        math_history_api='math.history.result.v1.1',execution_authority=False,
        training_authorized=False,trading_authorized=False,market={'venue':'bybit','market_type':'linear','symbol':'BTCUSDT'},
        strategy='test',dataset_id='a'*64,snapshot_fingerprint='b'*64,review_fingerprint='c'*64,result_receipt='d'*64,
        source={'units':{'price':'USDT/BTC','time':'UTC_MS'},'identity':{'source_revision':'a'*40}},
        observed_prices=[dict(event_end_ms=60000,available_at_ms=61000,watermark_ms=60000,value=101.0)],
        forecast_points=[dict(feature_event_end_ms=60000,feature_available_at_ms=61000,decision_ms=61000,
            target_event_end_ms=120000,value=102.5,request_digest='e'*64)],oos_metrics={'net_pnl':2.0}))

class AdmissionTests(unittest.TestCase):
    def admit(self,p):
        from terminan import history_overlay
        return history_overlay.admit(json.dumps(p).encode())

    def test_float_receipt_preserves_values_and_unknown_metadata(self):
        p=packet();r=self.admit(p)
        self.assertEqual(r['layers'][0]['points'][0]['value'],102.5)
        self.assertEqual(r['observations'][0]['available'],61000)
        self.assertEqual(r['metadata']['model_version'],'UNKNOWN')
        self.assertIsNone(r['oos'])  # missing publication clock must not expose scores
        self.assertEqual(r['integrity'],'SHA256_MATCH')
        self.assertEqual(r['authenticity'],'UNATTESTED')

    def test_tampered_bytes_are_rejected(self):
        p=packet();p['forecast_points'][0]['value']=500
        with self.assertRaisesRegex(ValueError,'DIGEST_MISMATCH'):self.admit(p)

    def test_rehashed_bad_clocks_and_authority_are_rejected(self):
        for field,value in [('decision_ms',120000),('feature_available_at_ms',62000),('target_event_end_ms',2**53)]:
            p=packet();p['forecast_points'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.admit(seal(p))
        for mutate in [lambda p:p.update(source_authenticity='VERIFIED'),lambda p:p.update(trading_authorized=True),
                       lambda p:p.update(mathematicallyVerified=True),lambda p:p.update(units={'price':'USD/BTC'})]:
            p=packet();mutate(p)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):self.admit(seal(p))

    def test_duplicate_json_keys_nonfinite_and_deep_inputs_are_rejected(self):
        from terminan import history_overlay
        for raw in [b'{"schema":1,"schema":2}',b'{"x":NaN}',b'['*100+b'0'+b']'*100]:
            with self.subTest(raw=raw[:30]),self.assertRaises(ValueError):history_overlay.admit(raw)

    def test_published_oos_must_follow_all_source_availability(self):
        p=packet();p.update(oos_available_at_ms=61000,split_receipts={'test':{'start_ms':60000,'end_ms':61000}})
        self.assertEqual(self.admit(seal(p))['oos']['available'],61000)
        p['oos_available_at_ms']=60000
        with self.assertRaises(ValueError):self.admit(seal(p))

    def test_nested_trust_promotion_and_invalid_metadata_are_rejected(self):
        for mutate in [lambda p:p['source'].update(source_authenticity='VERIFIED'),
                       lambda p:p.update(split_receipts=[]),
                       lambda p:p['source'].update(execution_authority=True),
                       lambda p:p['forecast_points'][0].update(feature_event_end_ms=59000)]:
            p=packet();mutate(p)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):self.admit(seal(p))

    def test_split_metadata_does_not_leak_future_scores(self):
        p=packet();p.update(oos_available_at_ms=61000,split_receipts={'test':{'start_ms':60000,'end_ms':61000,'metrics':{'net_pnl':987654321}}})
        r=self.admit(seal(p))
        self.assertNotIn('987654321',json.dumps(r['metadata']))

    def test_provenance_cannot_smuggle_oos_or_observation_values(self):
        p=packet();p['source']['oos_metrics']={'net_pnl':987654321}
        p['model']={'commit':'a'*40,'metrics':{'net_pnl':987654321}}
        r=self.admit(seal(p))
        self.assertNotIn('987654321',json.dumps(r['metadata']))

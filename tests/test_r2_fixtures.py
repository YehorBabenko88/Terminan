import copy
import unittest
from terminan.synthetic_contracts import fixtures, validate_fixture

class FixtureContracts(unittest.TestCase):
    def test_versioned_pinned_sources_and_provenance(self):
        for raw in fixtures():
            view=validate_fixture(raw,raw['observed_at_ms'])
            self.assertEqual(view['mode'],'SYNTHETIC')
            self.assertIn(view['state'],('HISTORICAL','PARTIAL'))
            self.assertEqual(view['runtime_source'],'NONE')

    def test_negative_contract_matrix(self):
        base=fixtures()[0]
        mutations=[
            ('SCHEMA_MISMATCH',lambda r:r.update(schema_version=99)),
            ('INVALID_PROVENANCE',lambda r:r['provenance'].update(kind='LIVE')),
            ('INVALID_PROVENANCE',lambda r:r['provenance'].update(source_sha='0'*40)),
            ('INVALID_DATA',lambda r:r['rows'][0].update(t=True)),
            ('INVALID_DATA',lambda r:r['rows'][0].update(c=float('nan'))),
            ('FUTURE_LEAKAGE',lambda r:r['rows'][0].update(available_at_ms=r['observed_at_ms']+1)),
        ]
        for expected,mutate in mutations:
            raw=copy.deepcopy(base);mutate(raw)
            view=validate_fixture(raw,raw['observed_at_ms'])
            self.assertEqual(view['state'],expected);self.assertEqual(view['rows'],[])

    def test_freshness_coverage_and_unavailability(self):
        raw=fixtures()[0];now=raw['observed_at_ms']
        self.assertEqual(validate_fixture(raw,now+999999)['state'],'STALE')
        raw['rows']=raw['rows'][::2]
        self.assertEqual(validate_fixture(raw,now)['state'],'PARTIAL')
        raw['source_state']='UNAVAILABLE'
        self.assertEqual(validate_fixture(raw,now)['state'],'UNAVAILABLE')

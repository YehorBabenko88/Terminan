import copy,json,unittest
from decimal import Decimal
import test_causal_session as helpers
class FundingGapTests(unittest.TestCase):
 setUp=helpers.SessionTests.setUp
 create=helpers.SessionTests.create
 session=helpers.SessionTests.session
 accept=helpers.SessionFlowTests.accept
 opened=helpers.SessionFlowTests.opened
 def test_explicit_unknown_invalidates_all_three_pending_phases_before_new_decisions(self):
  for phase in ('DECIDED','ENTRY_SELECTED','EXIT_DECIDED'):
   with self.subTest(phase=phase):
    s,_=self.opened();ident=8;event=4301;now=4310
    if phase!='DECIDED':self.accept(s,helpers.source_packet([helpers.book_row(8,4310)],7,4320),4320);ident=9;event=4415;now=4420
    if phase=='EXIT_DECIDED':self.accept(s,helpers.source_packet([helpers.book_row(9,4410)],8,4420),4420);ident=10;event=4421;now=4430
    before=s.account.snapshot()['reservations'][0];book_before=s._state['BTCUSDT']['strategy'].snapshot()['cursor'];quote_before=copy.deepcopy(s._state['BTCUSDT']['book'])
    row=helpers.funding_row(ident,known=False,event=event)
    for key in ('funding_rate','funding_interval_hour','next_funding_time'):row['payload'][key]=None
    packet=helpers.source_packet([row],ident-1,now);original=copy.deepcopy(packet);self.assertEqual(packet['funding_status'],'UNAVAILABLE');self.accept(s,packet,now);after=s.account.snapshot()['reservations'][0]
    self.assertEqual(after['status'],'UNCERTAIN');self.assertEqual(after['uncertainty'],'SOURCE_GAP');self.assertEqual(after['candidate']['funding'],before['candidate']['funding']);self.assertEqual(packet,original)
    if 'close_decision' not in before:self.assertNotIn('close_decision',after)
    else:self.assertEqual(after['close_decision'],before['close_decision'])
    book_after=s._state['BTCUSDT']['strategy'].snapshot()['cursor'];self.assertEqual(book_after['epochs'],book_before['epochs']);self.assertEqual(book_after['book'],book_before['book']);self.assertEqual(s._state['BTCUSDT']['book'],quote_before)
    for offset,delta in enumerate((10,150,170),1):self.accept(s,helpers.source_packet([helpers.book_row(ident+offset,now+delta,'102','102.1')],ident+offset-1,now+delta+10),now+delta+10)
    body=json.loads(s.publication_artifact().artifact_json);self.assertEqual(body['row_count'],0);self.assertEqual(s.account.snapshot()['reservations'][0]['status'],'UNCERTAIN');self.assertEqual(Decimal(s.account.snapshot()['reserved_usdt']),Decimal('100.1'))
   self.temp.cleanup();self.setUp()
 def test_omitted_fields_are_distinct_from_an_explicit_unknown(self):
  s,_=self.opened();before=copy.deepcopy(s.account.snapshot()['reservations'][0]['candidate']['funding']);row=helpers.stored_row(8,'derivatives_ticker',{'funding_rate':'0.0001'},4301,4302);p=helpers.source_packet([row],7,4310);self.assertEqual(p['funding_status'],'UNAVAILABLE');self.accept(s,p,4310);r=s.account.snapshot()['reservations'][0];self.assertEqual(r['status'],'DECIDED');self.assertEqual(r['candidate']['funding'],before);self.assertIsNone(s._state['BTCUSDT']['funding'])
 def test_complete_explicit_unavailable_row_invalidates_without_fake_numeric_change(self):
  s,_=self.opened();p=helpers.source_packet([helpers.funding_row(8,known=False,event=4301)],7,4310);self.accept(s,p,4310);r=s.account.snapshot()['reservations'][0];self.assertEqual(r['status'],'UNCERTAIN');self.assertEqual(r['uncertainty'],'SOURCE_GAP')

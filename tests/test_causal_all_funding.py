import copy,json,unittest
from decimal import Decimal
import test_causal_session as h
class AllFundingRowsTests(unittest.TestCase):
 setUp=h.SessionTests.setUp
 create=h.SessionTests.create
 session=h.SessionTests.session
 accept=h.SessionFlowTests.accept
 opened=h.SessionFlowTests.opened
 def stage(self,phase):
  s,_=self.opened();ident=8;event=4301;now=4340
  if phase!='DECIDED':self.accept(s,h.source_packet([h.book_row(8,4310)],7,4320),4320);ident=9;event=4415;now=4450
  if phase=='EXIT_DECIDED':self.accept(s,h.source_packet([h.book_row(9,4410)],8,4420),4420);ident=10;event=4421;now=4460
  return s,ident,event,now
 def rows(self,ident,event,pattern):
  rows=[]
  for offset,kind in enumerate(pattern):
   row=h.funding_row(ident+offset,known=kind!='unknown',event=event+offset*2)
   if kind=='unknown':
    for field in ('funding_rate','funding_interval_hour','next_funding_time'):row['payload'][field]=None
   if kind=='fresh':
    for proof in row['payload']['_field_observations']['fields'].values():proof.update(event_ms=event+offset*2,observed_ms=event+offset*2)
   rows.append(row)
  return rows
 def test_any_visible_unknown_latches_all_phases_and_positions(self):
  for phase in ('DECIDED','ENTRY_SELECTED','EXIT_DECIDED'):
   for pattern in (('unknown','known'),('known','unknown','known'),('known','known','unknown'),('unknown','known','unknown','known')):
    with self.subTest(phase=phase,pattern=pattern):
     s,ident,event,now=self.stage(phase);before=s.account.snapshot()['reservations'][0];oldbook=copy.deepcopy(s._state['BTCUSDT']['strategy'].snapshot()['cursor']);p=h.source_packet(self.rows(ident,event,pattern),ident-1,now);original=copy.deepcopy(p);self.accept(s,p,now);record=s.account.snapshot()['reservations'][0]
     self.assertEqual(record['status'],'UNCERTAIN');self.assertEqual(record['uncertainty'],'SOURCE_GAP');self.assertEqual(record['candidate']['funding'],before['candidate']['funding']);self.assertEqual(p,original);self.assertIsNone(s._state['BTCUSDT']['funding'])
     current=s._state['BTCUSDT']['strategy'].snapshot()['cursor'];self.assertEqual(current['book'],oldbook['book']);self.assertEqual(current['epochs'],oldbook['epochs'])
     if 'close_decision' not in before:self.assertNotIn('close_decision',record)
     else:self.assertEqual(record['close_decision'],before['close_decision'])
     last=ident+len(pattern)-1
     for offset,delta in enumerate((10,150,170),1):self.accept(s,h.source_packet([h.book_row(last+offset,now+delta,'102','102.1')],last+offset-1,now+delta+10),now+delta+10)
     self.assertEqual(json.loads(s.publication_artifact().artifact_json)['row_count'],0);self.assertEqual(Decimal(s.account.snapshot()['reserved_usdt']),Decimal('100.1'))
    self.temp.cleanup();self.setUp()
 def test_known_rows_do_not_invalidate_without_a_gap(self):
  s,ident,event,now=self.stage('DECIDED');p=h.source_packet(self.rows(ident,event,('known','known')),ident-1,now);self.accept(s,p,now);self.assertEqual(s.account.snapshot()['reservations'][0]['status'],'DECIDED');self.assertIsNotNone(s._state['BTCUSDT']['funding'])
 def test_new_complete_proof_cannot_resurrect_a_gapped_pending_reservation(self):
  s,ident,event,now=self.stage('DECIDED');p=h.source_packet(self.rows(ident,event,('unknown','fresh')),ident-1,now);self.accept(s,p,now);self.assertEqual(s.account.snapshot()['reservations'][0]['status'],'UNCERTAIN');self.assertEqual(s.account.snapshot()['reservations'][0]['uncertainty'],'SOURCE_GAP')

 def test_earlier_complete_missing_proof_cannot_borrow_latest_known_status(self):
  s,ident,event,now=self.stage('DECIDED');row=h.funding_row(ident,known=False,event=event);last=h.funding_row(ident+1,event=event+2);p=h.source_packet([row,last],ident-1,now);self.assertEqual(p['funding_status'],'KNOWN_SOURCE_FIELDS');self.accept(s,p,now);self.assertEqual(s.account.snapshot()['reservations'][0]['uncertainty'],'SOURCE_GAP');self.assertIsNone(s._state['BTCUSDT']['funding'])
 def test_unknown_gap_precedes_an_earlier_confirmed_numeric_change(self):
  s,ident,event,now=self.stage('DECIDED');changed=h.funding_row(ident,next_ms='57600000',event=event);rows=[changed,*self.rows(ident+1,event+2,('unknown','known'))];self.accept(s,h.source_packet(rows,ident-1,now),now);self.assertEqual(s.account.snapshot()['reservations'][0]['uncertainty'],'SOURCE_GAP')
 def test_known_change_cannot_be_hidden_by_later_known_original_interval(self):
  s,ident,event,now=self.stage('DECIDED');rows=[h.funding_row(ident,next_ms='57600000',event=event),h.funding_row(ident+1,event=event+2)];self.accept(s,h.source_packet(rows,ident-1,now),now);self.assertEqual(s.account.snapshot()['reservations'][0]['uncertainty'],'FUNDING_CHANGED')
 def test_pre_gap_proof_is_not_readopted_in_later_packet_or_new_connection(self):
  s,ident,event,now=self.stage('DECIDED');self.accept(s,h.source_packet(self.rows(ident,event,('unknown','known')),ident-1,now),now);before=s._state['BTCUSDT']['strategy'].snapshot()['cursor'];row=h.funding_row(ident+2,event=now+1);row['payload']['_producer_connection']['connection_id']='c'*32;self.accept(s,h.source_packet([row],ident+1,now+10),now+10);self.assertIsNone(s._state['BTCUSDT']['funding']);self.assertEqual(s.account.snapshot()['reservations'][0]['status'],'UNCERTAIN');after=s._state['BTCUSDT']['strategy'].snapshot()['cursor'];self.assertEqual(after['book'],before['book']);self.assertEqual(after['epochs'],before['epochs'])
 def test_missing_canonical_assessment_capability_refuses_before_cursor_or_account_write(self):
  from unittest.mock import patch
  import market_data.paper_inputs as data
  s,ident,event,now=self.stage('DECIDED');before=s._state['BTCUSDT']['strategy'].snapshot();files={p.name:p.read_bytes() for p in self.root.iterdir()};p=h.source_packet(self.rows(ident,event,('unknown','known')),ident-1,now)
  with patch.object(data,'assess_paper_funding_rows',None),self.assertRaisesRegex(RuntimeError,'DATA_FUNDING_ROW_ASSESSMENT_REQUIRED'):self.accept(s,p,now)
  self.assertEqual(s._state['BTCUSDT']['strategy'].snapshot(),before);self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},files)

 def test_complete_known_but_nonintegral_schedule_cannot_fall_back_to_prior_interval(self):
  s,ident,event,now=self.stage('DECIDED');row=h.funding_row(ident,next_ms='28800000.1',event=event);last=h.funding_row(ident+1,event=event+2);p=h.source_packet([row,last],ident-1,now);self.assertEqual(p['funding_status'],'KNOWN_SOURCE_FIELDS');self.accept(s,p,now);r=s.account.snapshot()['reservations'][0];self.assertEqual(r['status'],'UNCERTAIN');self.assertEqual(r['uncertainty'],'SOURCE_GAP');self.assertIsNone(s._state['BTCUSDT']['funding'])

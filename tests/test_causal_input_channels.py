import copy,unittest
from datetime import datetime,timezone,timedelta
from market_data.paper_inputs import export_paper_inputs
from terminan.causal_inputs import CausalInputCursor
CONTEXT=dict(schema='market_data.public-market-connection.v1',venue='bybit',category='linear',endpoint='wss://stream.bybit.com/v5/public/linear',connection_id='a'*32,scope='PRODUCER_DECLARED_LOCAL_CONNECTION_NOT_REMOTE_AUTHENTICATION')
def packet(ident,kind,payload):
 ms=1000+ident*100;q=dict(symbol='BTCUSDT',after_id=ident-1,start_ms=0,end_ms=3001,as_of_ms=3000,max_age_ms=3000);epoch=datetime(1970,1,1,tzinfo=timezone.utc)
 return export_paper_inputs([dict(id=ident,symbol='BTCUSDT',source='bybit',event_type=kind,payload=payload,event_ts=epoch+timedelta(milliseconds=ms),ingest_ts=epoch+timedelta(milliseconds=ms+1))],q)
def book(sequence):return dict(best_bid='100',best_ask='101',sequence=sequence,update_id=sequence,_producer_connection=CONTEXT,_quality={'symbol':'BTCUSDT','feeds':{'orderbook':{'status':'available'}}})
class CausalChannelTests(unittest.TestCase):
 def test_funding_without_context_cannot_clear_book_epoch_or_sequence(self):
  c=CausalInputCursor('BTCUSDT');p=packet(1,'orderbook_snapshot',book(10));c.accept(p,expected_request=p['request']);before=c.snapshot();f=packet(2,'derivatives_ticker',dict(funding_rate=None));batch=c.accept(f,expected_request=f['request']);middle=c.snapshot()
  self.assertEqual(middle['epochs'],before['epochs']);self.assertEqual(middle['book'],before['book']);self.assertEqual(batch.changed_channels,());self.assertEqual(middle['cursor'],2)
  p=packet(3,'orderbook_snapshot',book(9))
  with self.assertRaises(ValueError):c.accept(p,expected_request=p['request'])
  self.assertEqual(c.snapshot(),middle)
 def test_funding_foreign_context_never_changes_book_channel(self):
  c=CausalInputCursor('BTCUSDT');p=packet(1,'orderbook_snapshot',book(10));c.accept(p,expected_request=p['request']);before=c.snapshot();context=dict(CONTEXT,connection_id='b'*32);p=packet(2,'derivatives_ticker',dict(funding_rate=None,_producer_connection=context));b=c.accept(p,expected_request=p['request']);self.assertEqual(c.snapshot()['epochs'],before['epochs']);self.assertEqual(c.snapshot()['book'],before['book']);self.assertEqual(b.changed_channels,())

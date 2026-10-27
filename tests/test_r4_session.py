import unittest
from terminan.r4_session import Session,validate_receipt
class R4SessionTests(unittest.TestCase):
 def test_owner_end_is_immutable_and_bound(self):
  session=Session();a=session.receipt('a'*40);validate_receipt(a,'a'*40)
  session.end();b=session.receipt('a'*40,a['session_id']);self.assertEqual(b['state'],'SESSION_ENDED');self.assertGreater(b['revision'],a['revision']);session.end();self.assertEqual(session.receipt('a'*40)['revision'],b['revision'])
  for nonce in ('b'*32,'',None):
   if nonce is None:continue
   with self.assertRaises(ValueError):session.receipt('a'*40,nonce)
 def test_receipt_schema_authority_and_identity(self):
  a=Session().receipt('a'*40)
  for key,value in [('version',True),('lease_ms',float('nan')),('state','LIVE_SOURCE_VERIFIED'),('authority','LIVE'),('epoch',0),('candidate_sha','b'*40)]:
   b=a.copy();b[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):validate_receipt(b,'a'*40)

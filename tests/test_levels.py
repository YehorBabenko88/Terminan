from contextlib import closing
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from threading import Thread
import unittest
from unittest.mock import patch

from terminan.levels import untouched_levels,merge_levels
from terminan.server import Handler

class LevelTests(unittest.TestCase):
    def test_high_low_touch_invalidation(self):
        h=3600000
        rows=[dict(t=0,h=100,l=90),dict(t=h,h=99,l=91),dict(t=2*h,h=101,l=92)]
        v=untouched_levels(rows,'1h',3*h)
        self.assertFalse(any(x['origin_ms']==0 and x['side']=='high' for x in v))
        self.assertTrue(any(x['origin_ms']==0 and x['side']=='low' for x in v))
    def test_no_future_candles(self):
        h=3600000
        self.assertEqual(untouched_levels([dict(t=0,h=5,l=1)],'1h',h-1),[])
    def test_incomplete_ignored(self):
        h=3600000
        self.assertEqual(untouched_levels([dict(t=0,h=5,l=1,complete=False)],'1h',h),[])
    def test_merge(self):
        h=3600000
        self.assertEqual(len(merge_levels({'1h':[dict(t=0,h=2,l=1)]},h)),2)
    def test_invalid(self):
        with self.assertRaises(ValueError): untouched_levels([], '1m', 0)

    def test_http_levels_does_not_read_unqualified_legacy_candles(self):
        with patch("terminan.server.data.candles") as legacy, \
                patch.object(Handler, "log_message"), \
                ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            worker = Thread(target=server.serve_forever)
            worker.start()
            try:
                with closing(HTTPConnection("127.0.0.1", server.server_port, timeout=5)) as client:
                    client.request("GET", "/api/levels?symbol=BTCUSDT")
                    with client.getresponse() as response:
                        self.assertEqual(response.status, 503)
                        self.assertEqual(json.load(response), {"error": "source unavailable"})
            finally:
                server.shutdown()
                worker.join()
        legacy.assert_not_called()

if __name__=='__main__':unittest.main()

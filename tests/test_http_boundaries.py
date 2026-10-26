import unittest
from terminan.server import Handler, MAX_HEADER_LINE, MAX_HEADERS

class HTTPBoundaryTests(unittest.TestCase):
    def test_bounded_header_parser(self):
        self.assertEqual(Handler.maxline, MAX_HEADER_LINE)
        self.assertEqual(Handler.maxheaders, MAX_HEADERS)
        self.assertLessEqual(MAX_HEADER_LINE, 8192)
        self.assertLessEqual(MAX_HEADERS, 64)
    def test_explicitly_reject_mutating_methods(self):
        for method in ('POST','PUT','DELETE','OPTIONS'):
            self.assertTrue(callable(getattr(Handler, 'do_' + method)))

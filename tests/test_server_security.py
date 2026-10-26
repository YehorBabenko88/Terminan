import unittest
from terminan.server import valid_host, MAX_TARGET_LENGTH, MAX_QUERY_FIELDS

class HostSecurityTests(unittest.TestCase):
    def test_loopback_only_host(self):
        for host in ('127.0.0.1:8765','localhost:8765','[::1]:8765','127.0.0.1'):
            self.assertTrue(valid_host(host,8765))
        for host in ('evil.example:8765','127.0.0.1.evil.example:8765','0.0.0.0:8765','127.0.0.1:9999','LOCALHOST:8765','localhost:8765,evil.example'):
            self.assertFalse(valid_host(host,8765))
    def test_limits(self):
        self.assertEqual(MAX_TARGET_LENGTH,2048)
        self.assertEqual(MAX_QUERY_FIELDS,12)

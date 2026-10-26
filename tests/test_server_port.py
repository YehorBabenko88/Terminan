import os
import unittest
from unittest.mock import patch
from terminan import server


class BindingTests(unittest.TestCase):
    def test_ls5_port_can_differ_from_grid_without_exposing_remote_listener(self):
        with patch.dict(os.environ,{'TERMINAN_HOST':'127.0.0.1','TERMINAN_PORT':'8766'}), patch.object(server,'ThreadingHTTPServer') as http:
            server.run()
            self.assertEqual(http.call_args.args[0],('127.0.0.1',8766))
            http.return_value.serve_forever.assert_called_once()

    def test_invalid_ports_are_rejected_before_binding(self):
        for value in ('0','65536','-1','8766.0','password',''):
            with self.subTest(value=value), patch.dict(os.environ,{'TERMINAN_HOST':'127.0.0.1','TERMINAN_PORT':value}), patch.object(server,'ThreadingHTTPServer') as http:
                with self.assertRaises(SystemExit):server.run()
                http.assert_not_called()

    def test_remote_host_is_still_rejected(self):
        with patch.dict(os.environ,{'TERMINAN_HOST':'0.0.0.0','TERMINAN_PORT':'8766'}), patch.object(server,'ThreadingHTTPServer') as http:
            with self.assertRaises(SystemExit):server.run()
            http.assert_not_called()

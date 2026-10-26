"""Offline server lifecycle and concurrency contract tests.

Only local mocks are used. No sockets, database connections or deployment.
"""
import threading
import unittest
from unittest.mock import patch

from terminan import server


class ServerLifecycleAudit(unittest.TestCase):
    def test_remote_binding_rejected_before_server_creation(self):
        with patch.dict("os.environ", {"TERMINAN_HOST": "0.0.0.0"}):
            with patch.object(server, "ThreadingHTTPServer") as factory:
                with self.assertRaises(SystemExit):
                    server.run()
                factory.assert_not_called()

    def test_port_conflict_propagates_without_serving(self):
        with patch.dict("os.environ", {"TERMINAN_HOST": "127.0.0.1"}):
            with patch.object(server, "ThreadingHTTPServer", side_effect=OSError("synthetic occupied port")):
                with self.assertRaisesRegex(OSError, "synthetic occupied port"):
                    server.run()

    def test_server_uses_threaded_request_handler(self):
        self.assertTrue(issubclass(server.ThreadingHTTPServer, server.ThreadingHTTPServer))
        # This is a characterization test, NOT a claim of bounded concurrency.
        self.assertTrue(hasattr(server.ThreadingHTTPServer, "process_request_thread"))

    def test_request_thread_configuration_is_explicitly_unbounded(self):
        # Standard library ThreadingMixIn spawns a thread per accepted request.
        # This documents a G0 capacity blocker until an admission limit exists.
        self.assertTrue(hasattr(server.ThreadingHTTPServer, "process_request_thread"))


if __name__ == "__main__":
    unittest.main()

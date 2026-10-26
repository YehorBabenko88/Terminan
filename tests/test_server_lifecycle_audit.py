"""Offline server lifecycle and concurrency contract tests.

Only local mocks are used. No sockets, database connections or deployment.
"""
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

    def test_loopback_server_startup_uses_expected_port(self):
        from unittest.mock import MagicMock
        fake = MagicMock()
        with patch.dict("os.environ", {"TERMINAN_HOST": "127.0.0.1"}):
            with patch.object(server, "ThreadingHTTPServer", return_value=fake) as factory:
                server.run()
        factory.assert_called_once_with(("127.0.0.1", 8765), server.Handler)
        fake.serve_forever.assert_called_once_with()

    def test_threaded_handler_has_no_explicit_admission_limit(self):
        # Characterization only: no capacity PASS is implied.
        self.assertTrue(hasattr(server.ThreadingHTTPServer, "process_request_thread"))


if __name__ == "__main__":
    unittest.main()

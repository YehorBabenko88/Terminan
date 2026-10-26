"""Grid connection transaction read-only verification with mock psycopg."""
import os
import sys
import types
import unittest
from unittest.mock import patch
from terminan import data


class FakeCursor:
    def __init__(self, state):
        self.state = state
        self.calls = []
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def execute(self, sql, params=None):
        self.calls.append((sql, params))
    def fetchone(self):
        return self.state
    def fetchall(self):
        return [(1,)]


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_value = cursor
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def cursor(self):
        return self.cursor_value


class ReadOnlyTransaction(unittest.TestCase):
    def invoke(self, state):
        cur = FakeCursor(state)
        fake = types.SimpleNamespace(connect=lambda *a, **k: FakeConnection(cur))
        with patch.dict(os.environ, {"TERMINAN_GRID_DSN": "host=synthetic"}):
            with patch.dict(sys.modules, {"psycopg": fake}):
                try:
                    result = data.grid_query("SELECT 1", ())
                    return cur.calls, result
                except RuntimeError:
                    self.assertEqual(len(cur.calls), 1)
                    raise

    def test_read_only_precedes_data_query(self):
        calls, result = self.invoke(("on",))
        self.assertEqual(calls, [("SHOW transaction_read_only", None), ("SELECT 1", ())])
        self.assertEqual(result, [(1,)])

    def test_reject_writeable_or_unknown(self):
        for state in (("off",), None, (), ("unknown",)):
            with self.subTest(state=state):
                with self.assertRaises(RuntimeError):
                    self.invoke(state)


if __name__ == "__main__":
    unittest.main()

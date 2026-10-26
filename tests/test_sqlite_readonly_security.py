import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from terminan.data import sqlite_ro

class ReadOnlySQLiteTests(unittest.TestCase):
    def test_existing_database_is_query_only(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fixture.db'
            with sqlite3.connect(path) as writable:
                writable.execute('CREATE TABLE records (value INTEGER)')
                writable.execute('INSERT INTO records VALUES (7)')
            with patch.dict(os.environ, {'TERMINAN_STRATTESTER_DB': str(path)}):
                con = sqlite_ro('TERMINAN_STRATTESTER_DB')
                try:
                    self.assertEqual(con.execute('SELECT value FROM records').fetchone()[0], 7)
                    self.assertEqual(con.execute('PRAGMA query_only').fetchone()[0], 1)
                    with self.assertRaises(sqlite3.OperationalError):
                        con.execute('INSERT INTO records VALUES (8)')
                finally:
                    con.close()
            with sqlite3.connect(path) as check:
                self.assertEqual(check.execute('SELECT COUNT(*) FROM records').fetchone()[0], 1)

    def test_missing_file_is_not_created(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'missing.db'
            with patch.dict(os.environ, {'TERMINAN_RESULTS_DB': str(path)}):
                self.assertIsNone(sqlite_ro('TERMINAN_RESULTS_DB'))
            self.assertFalse(path.exists())

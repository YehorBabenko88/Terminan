"""Local, append-only receipts for Terminan's offline paper replay."""

from contextlib import closing
from hashlib import sha256
import json
import sqlite3


_APPLICATION_ID = 0x54505231  # TPR1


class ReplayConflict(ValueError):
    """A run ID is already bound to a different request."""


def canonical_json(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid JSON replay request") from exc


class PaperReplayLedger:
    """Store finalized receipts in a dedicated SQLite file on a local volume."""

    def __init__(self, path):
        self.path = path
        with closing(self._connect()) as database, database:
            if self._application_id(database) == _APPLICATION_ID:
                return
            database.execute("BEGIN IMMEDIATE")
            application_id = self._application_id(database)
            if application_id == _APPLICATION_ID:
                return
            if application_id or database.execute(
                "SELECT 1 FROM sqlite_schema LIMIT 1"
            ).fetchone():
                raise RuntimeError("paper replay requires a dedicated database")
            database.execute(
                "CREATE TABLE paper_replay_receipts ("
                "run_id TEXT PRIMARY KEY NOT NULL, "
                "request_sha256 TEXT NOT NULL, receipt TEXT NOT NULL)"
            )
            database.execute(f"PRAGMA application_id = {_APPLICATION_ID}")

    def _connect(self):
        return sqlite3.connect(self.path, timeout=5)

    @staticmethod
    def _application_id(database):
        return database.execute("PRAGMA application_id").fetchone()[0]

    def read(self, run_id, request_sha256):
        with closing(self._connect()) as database, database:
            database.execute("BEGIN")
            if self._application_id(database) != _APPLICATION_ID:
                raise RuntimeError("paper replay requires a dedicated database")
            return self._read(database, run_id, request_sha256)

    @staticmethod
    def _read(database, run_id, request_sha256):
        row = database.execute(
            "SELECT request_sha256, receipt FROM paper_replay_receipts "
            "WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return None
        stored_request_sha256, raw_receipt = row
        try:
            receipt = json.loads(raw_receipt)
            digest = receipt.pop("result_sha256")
            if (digest != sha256(canonical_json(receipt)).hexdigest()
                    or receipt["run_id"] != run_id
                    or receipt["request_sha256"] != stored_request_sha256
                    or receipt["status"] != "OFFLINE_UNATTESTED"
                    or receipt["provenance"] != "CALLER_SUPPLIED_UNATTESTED"
                    or receipt["execution_authority"] is not False
                    or receipt["trading_authorized"] is not False):
                raise ValueError("invalid receipt")
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise RuntimeError("paper replay receipt integrity failure") from exc
        if stored_request_sha256 != request_sha256:
            raise ReplayConflict("paper replay run_id already used for another request")
        receipt["result_sha256"] = digest
        return receipt

    def record(self, receipt):
        run_id = receipt["run_id"]
        request_sha256 = receipt["request_sha256"]
        with closing(self._connect()) as database, database:
            database.execute("BEGIN IMMEDIATE")
            if self._application_id(database) != _APPLICATION_ID:
                raise RuntimeError("paper replay requires a dedicated database")
            database.execute(
                "INSERT INTO paper_replay_receipts VALUES (?, ?, ?) "
                "ON CONFLICT(run_id) DO NOTHING",
                (run_id, request_sha256, canonical_json(receipt).decode("utf-8")),
            )
            return self._read(database, run_id, request_sha256)

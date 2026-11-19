"""Local, append-only receipts for Terminan's offline paper replay."""

from contextlib import closing, contextmanager
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
import sqlite3


_APPLICATION_ID = 0x54505231  # TPR1
_META_RECEIPT = {
    "schema": "meta.persisted-state.digest.v1",
    "table": "paper_fills",
    "source_status": "UNVERIFIED_LOCAL_READBACK",
    "execution_authority": False,
    "trading_authorized": False,
}


def _meta_digest():
    return sha256(b"meta.persisted-state.digest.v1\0paper_fills\0")


def _add_meta_row(digest, raw):
    digest.update(len(raw).to_bytes(4, "big"))
    digest.update(raw)


def _encode_meta_fill(row):
    if (type(row) not in (tuple, list) or len(row) != 10
            or type(row[0]) is not int or not -(2**63) <= row[0] < 2**63
            or any(type(value) is not str for value in row[1:])):
        raise ValueError("invalid legacy paper fill row")
    raw = canonical_json(row)
    if len(raw) > 262_144:
        raise ValueError("legacy paper fill row exceeds byte limit")
    try:
        for index in (3, 4, 6, 7, 8):
            value = Decimal(row[index])
            if not value.is_finite() or str(value) != row[index]:
                raise ValueError("expected canonical finite Decimal text")
        stamp = datetime.fromisoformat(row[9])
        if (not row[9].endswith("+00:00")
                or stamp.isoformat(timespec="microseconds") != row[9]):
            raise ValueError("expected canonical UTC timestamp")
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("invalid legacy fill decimal or timestamp") from exc
    return raw


def _validate_meta_source(source_id):
    if type(source_id) is not str or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", source_id):
        raise ValueError("invalid legacy fill source identifier")


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

    @contextmanager
    def _paper_event_transaction(self, *, write):
        with closing(self._connect()) as database, database:
            if not write:
                database.execute("PRAGMA query_only = ON")
            else:
                database.execute("PRAGMA synchronous = FULL")
            database.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            if self._application_id(database) != _APPLICATION_ID:
                raise RuntimeError("paper replay requires a dedicated database")
            yield database

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

    def import_meta_fills(self, source_id, rows, source_receipt):
        """Archive one immutable Meta digest-v1 snapshot from a trusted export.

        The caller provides canonical SQL rows and the separately captured
        source receipt for that same frozen snapshot. This local operator API
        never opens the source database or grants execution authority. Use a
        stable opaque identifier for retries and a new ID for a new snapshot.
        """
        _validate_meta_source(source_id)
        if (type(source_receipt) is not dict
                or source_receipt.keys() != _META_RECEIPT.keys() | {"row_count", "sha256"}
                or any(type(source_receipt[key]) is not type(expected)
                       or source_receipt[key] != expected
                       for key, expected in _META_RECEIPT.items())):
            raise ValueError("unsupported legacy fill source receipt")
        count = source_receipt["row_count"]
        expected = source_receipt["sha256"]
        if (type(count) is not int or not 0 <= count <= 1_000_000
                or type(expected) is not str or not re.fullmatch(r"[0-9a-f]{64}", expected)):
            raise ValueError("invalid legacy fill source digest or row count")

        with closing(self._connect()) as database, database:
            database.execute("BEGIN IMMEDIATE")
            if self._application_id(database) != _APPLICATION_ID:
                raise RuntimeError("paper replay requires a dedicated database")
            database.execute(
                "CREATE TABLE IF NOT EXISTS meta_fill_archives ("
                "source_id TEXT PRIMARY KEY NOT NULL, row_count INTEGER NOT NULL, "
                "sha256 TEXT NOT NULL)"
            )
            database.execute(
                "CREATE TABLE IF NOT EXISTS meta_fill_rows ("
                "source_id TEXT NOT NULL, fill_id INTEGER NOT NULL, row_json BLOB NOT NULL, "
                "PRIMARY KEY (source_id, fill_id))"
            )
            archive = self._meta_archive(database, source_id)
            if archive is not None and archive != (count, expected):
                raise ReplayConflict("legacy fill source ID already bound to a different snapshot")
            digest = _meta_digest()
            total = size = 0
            previous = None
            for row in rows:
                raw = _encode_meta_fill(row)
                total += 1
                size += len(raw)
                if (total > count or size > 2**30
                        or (previous is not None and previous >= row[0])):
                    raise ValueError("legacy fill export exceeds bounds or IDs are out of order")
                previous = row[0]
                _add_meta_row(digest, raw)
                if archive is None:
                    database.execute("INSERT INTO meta_fill_rows VALUES (?, ?, ?)",
                                     (source_id, row[0], raw))
            if (total, digest.hexdigest()) != (count, expected):
                raise ValueError("legacy fill export does not match source receipt")
            if archive is None:
                database.execute("INSERT INTO meta_fill_archives VALUES (?, ?, ?)",
                                 (source_id, count, expected))
            self._verify_meta_archive(database, source_id, (count, expected))
        return dict(_META_RECEIPT, row_count=count, sha256=expected)

    def restore_meta_fills(self, source_id):
        """Yield verified canonical rows from a single read-only snapshot.

        Exhaust the iterator or close it promptly to release the reader lock.
        """
        _validate_meta_source(source_id)
        with closing(self._connect()) as database, database:
            database.execute("PRAGMA query_only = ON")
            database.execute("BEGIN")
            if self._application_id(database) != _APPLICATION_ID:
                raise RuntimeError("paper replay requires a dedicated database")
            archive = self._meta_archive(database, source_id)
            if archive is None:
                raise KeyError(source_id)
            self._verify_meta_archive(database, source_id, archive)
            for _, raw in self._meta_rows(database, source_id):
                yield json.loads(raw)

    @staticmethod
    def _meta_archive(database, source_id):
        if not database.execute(
            "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = 'meta_fill_archives'"
        ).fetchone():
            return None
        return database.execute(
            "SELECT row_count, sha256 FROM meta_fill_archives WHERE source_id = ?",
            (source_id,),
        ).fetchone()

    @staticmethod
    def _meta_rows(database, source_id):
        return database.execute(
            "SELECT fill_id, row_json FROM meta_fill_rows WHERE source_id = ? ORDER BY fill_id",
            (source_id,),
        )

    def _verify_meta_archive(self, database, source_id, archive):
        digest = _meta_digest()
        total = 0
        for fill_id, raw in self._meta_rows(database, source_id):
            if (type(raw) is not bytes or len(raw) > 262_144
                    or not raw.startswith(f"[{fill_id},".encode("ascii"))):
                raise RuntimeError("legacy fill archive integrity failure")
            total += 1
            if total > archive[0]:
                raise RuntimeError("legacy fill archive integrity failure")
            _add_meta_row(digest, raw)
        if (total, digest.hexdigest()) != archive:
            raise RuntimeError("legacy fill archive integrity failure")

"""Preserve frozen Strattester research history without admitting it to execution."""

from hashlib import sha256
import json
from math import isinf, isnan
import re

from .paper_ledger import ReplayConflict, canonical_json


_SCHEMA = "terminan.strattester.result_archive.v1"
_TABLES = {"research_results": 4, "staged_research_results": 1}
_MAX_ROWS = 1_000_000
_MAX_ROW_BYTES = 262_144
_MAX_TABLE_BYTES = 2**30


def _check_tables(tables):
    if type(tables) is not dict or tables.keys() != _TABLES.keys():
        raise ValueError("both Strattester result tables are required")


def _snapshot_digest(value):
    if type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("invalid source snapshot SHA-256")
    return value


def _source_id(value):
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", value):
        raise ValueError("invalid archive source identity")


def _pack(table, row):
    # Preserve the original SQLite REAL and metrics TEXT. Old metrics can
    # contain non-standard JSON; this archive never interprets them.
    start = int(table == "staged_research_results")
    if type(row) not in (list, tuple) or len(row) != start + 9:
        raise ValueError("invalid Strattester result width")
    created_at, metrics, job, lease, generation = row[start + 4:]
    if (any(type(value) is not str for value in row[:start + 4])
            or type(created_at) is not float or isnan(created_at)
            or type(metrics) is not str
            or (job is not None and type(job) is not str)
            or any(type(value) is not int or not -(2**63) <= value < 2**63
                   for value in (lease, generation))):
        raise ValueError("invalid Strattester result fields")
    # SQLite REAL can preserve either infinity even though JSON numbers
    # cannot. Encode it as a tagged string in this position only.
    encoded = list(row)
    if isinf(created_at):
        encoded[start + 4] = created_at.hex()
    raw = canonical_json(encoded)
    if len(raw) > _MAX_ROW_BYTES:
        raise ValueError("Strattester result row byte limit")
    return tuple(row[:_TABLES[table]]), raw


def _scan(table, rows, record=None):
    digest = sha256(_SCHEMA.encode("ascii") + b"\0" + table.encode("ascii") + b"\0")
    previous = None
    size = count = 0
    for row in rows:
        key, raw = _pack(table, row)
        count += 1
        size += len(raw)
        if count > _MAX_ROWS or size > _MAX_TABLE_BYTES:
            raise ValueError("Strattester archive limit")
        if previous is not None and key <= previous:
            raise ValueError("duplicate or unordered Strattester result key")
        previous = key
        digest.update(len(raw).to_bytes(4, "big"))
        digest.update(raw)
        if record is not None:
            record(count, raw)
    return {"row_count": count, "sha256": digest.hexdigest()}


def _receipt(snapshot_sha256, tables):
    return {
        "schema": _SCHEMA,
        "source_snapshot_sha256": _snapshot_digest(snapshot_sha256),
        "tables": tables,
        "source_status": "CALLER_SUPPLIED_UNATTESTED",
        "execution_authority": False,
        "trading_authorized": False,
    }


def research_result_receipt(snapshot_sha256, tables):
    """Hash both ordered result tables from a single frozen SQLite backup."""
    _check_tables(tables)
    return _receipt(snapshot_sha256, {table: _scan(table, tables[table]) for table in _TABLES})


class ResearchArchive:
    """Operator-only historical import/export in Terminan's existing ledger."""

    def __init__(self, ledger):
        self._ledger = ledger

    def import_snapshot(self, source_id, tables, receipt):
        """Import both original tables atomically, checking the source receipt."""
        _source_id(source_id)
        _check_tables(tables)
        if type(receipt) is not dict:
            raise ValueError("invalid Strattester archive receipt")
        expected_raw = canonical_json(receipt)
        if len(expected_raw) > 4096:
            raise ValueError("Strattester archive receipt byte limit")
        expected = json.loads(expected_raw)
        source_sha = _snapshot_digest(expected.get("source_snapshot_sha256"))

        with self._ledger._paper_event_transaction(write=True) as database:
            database.execute(
                "CREATE TABLE IF NOT EXISTS archived_research_v1 ("
                "source_id TEXT PRIMARY KEY NOT NULL, receipt BLOB NOT NULL)"
            )
            database.execute(
                "CREATE TABLE IF NOT EXISTS archived_research_rows_v1 ("
                "source_id TEXT NOT NULL, table_name TEXT NOT NULL, ordinal INTEGER NOT NULL, "
                "row_json BLOB NOT NULL, PRIMARY KEY (source_id, table_name, ordinal))"
            )
            archived = self._stored_receipt(database, source_id)
            if archived is not None and archived != expected_raw:
                raise ReplayConflict("source ID already bound to another research snapshot")
            received = {}
            for table in _TABLES:
                def insert(ordinal, raw):
                    database.execute("INSERT INTO archived_research_rows_v1 VALUES (?, ?, ?, ?)",
                                     (source_id, table, ordinal, raw))

                received[table] = _scan(table, tables[table], insert if archived is None else None)
            result = _receipt(source_sha, received)
            if canonical_json(result) != expected_raw:
                raise ValueError("Strattester rows do not match the source receipt")
            self._verify(database, source_id, result)
            if archived is None:
                database.execute("INSERT INTO archived_research_v1 VALUES (?, ?)",
                                 (source_id, expected_raw))
        return result

    @staticmethod
    def _stored_receipt(database, source_id):
        if database.execute(
            "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = 'archived_research_v1'"
        ).fetchone() is None:
            return None
        row = database.execute("SELECT receipt FROM archived_research_v1 WHERE source_id = ?",
                               (source_id,)).fetchone()
        return None if row is None else row[0]

    @staticmethod
    def _rows(database, source_id, table):
        rows = database.execute(
            "SELECT ordinal, row_json FROM archived_research_rows_v1 "
            "WHERE source_id = ? AND table_name = ? ORDER BY ordinal", (source_id, table))
        for expected, (ordinal, raw) in enumerate(rows, 1):
            if ordinal != expected or type(raw) is not bytes or len(raw) > _MAX_ROW_BYTES:
                raise ValueError("invalid archived row")
            row = json.loads(raw)
            stamp = int(table == "staged_research_results") + 4
            if type(row) is list and len(row) > stamp and row[stamp] in ("inf", "-inf"):
                row[stamp] = float.fromhex(row[stamp])
            if _pack(table, row)[1] != raw:
                raise ValueError("invalid archived row encoding")
            yield tuple(row)

    def _verify(self, database, source_id, receipt):
        try:
            tables = {table: _scan(table, self._rows(database, source_id, table))
                      for table in _TABLES}
            if canonical_json(_receipt(receipt["source_snapshot_sha256"], tables)) != canonical_json(receipt):
                raise ValueError("archived rows do not match receipt")
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("Strattester archive integrity failure") from exc

    def read_snapshot(self, source_id):
        """Yield (table, disposition, original row) after verifying both tables."""
        _source_id(source_id)
        with self._ledger._paper_event_transaction(write=False) as database:
            archived = self._stored_receipt(database, source_id)
            if archived is None:
                raise KeyError(source_id)
            try:
                receipt = json.loads(archived)
            except (TypeError, ValueError) as exc:
                raise RuntimeError("Strattester archive integrity failure") from exc
            self._verify(database, source_id, receipt)
            for table in _TABLES:
                for row in self._rows(database, source_id, table):
                    if table == "staged_research_results":
                        disposition = "STAGED_UNVERIFIED"
                    elif row[6] is None:
                        disposition = "LEGACY_UNFENCED"
                    else:
                        disposition = "PUBLISHED_UNVERIFIED"
                    yield table, disposition, row

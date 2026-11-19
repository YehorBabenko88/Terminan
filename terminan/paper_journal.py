"""Restartable, per-event journal for the existing simulated PaperEngine."""

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Context, Decimal, InvalidOperation, localcontext
from hashlib import sha256
import json
import re
from threading import Lock

from .paper import STRATEGIES, ClosedMinute, ExecutionTrade, PaperEngine, _serialize
from .paper_ledger import ReplayConflict, canonical_json


_EVENT_SCHEMA = "terminan.paper.event.v1"
_ACK_SCHEMA = "terminan.paper.event.ack.v1"
_STRATEGY = "meta.poc.next_minute"
_FIELDS = {"schema", "sequence", "kind", "event_time"}
_OPTIONS = {"enabled": {"enabled"}, "closed_minute": {"poc", "complete"},
            "trade": {"price"}, "gap": set()}


def _utc(value):
    if type(value) is not str or len(value) > 32 or not value.endswith("+00:00"):
        raise ValueError("UTC timestamp required")
    parsed = datetime.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("canonical UTC timestamp required")
    return parsed


def _price(value):
    if type(value) is not str or len(value) > 64:
        raise ValueError("paper price must be a bounded Decimal string")
    try:
        price = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid paper price") from exc
    if not price.is_finite() or price <= 0 or not -100 <= price.adjusted() <= 100:
        raise ValueError("invalid paper price")
    return price


def _validate(event):
    if (type(event) is not dict or event.get("schema") != _EVENT_SCHEMA
            or type(event.get("sequence")) is not int
            or not 1 <= event["sequence"] < 2**63
            or type(event.get("kind")) is not str
            or event["kind"] not in _OPTIONS
            or set(event) != _FIELDS | _OPTIONS[event["kind"]]):
        raise ValueError("invalid paper journal event")
    _utc(event["event_time"])
    if event["kind"] == "enabled" and type(event["enabled"]) is not bool:
        raise ValueError("invalid paper enabled flag")
    if event["kind"] == "closed_minute":
        if type(event["complete"]) is not bool:
            raise ValueError("invalid paper completeness flag")
        _price(event["poc"])
    if event["kind"] == "trade":
        _price(event["price"])


def _available_at(event):
    stamp = _utc(event["event_time"])
    return stamp + timedelta(minutes=1) if event["kind"] == "closed_minute" else stamp


class PaperJournal:
    """One source ID, run ID and instrument using strategy v1 default policy.

    Submit full ordered events starting at sequence 1 from a replayable caller.
    Every acknowledgement is returned after commit. A changed retry or skipped
    sequence is rejected. If a commit fails after computing a transition,
    discard this instance and reopen the same journal before retrying.
    """

    def __init__(self, ledger, source_id, run_id, symbol):
        for identity in (source_id, run_id):
            if type(identity) is not str or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", identity):
                raise ValueError("invalid paper journal identity")
        if type(symbol) is not str or not re.fullmatch(r"[A-Z0-9]{2,30}", symbol):
            raise ValueError("invalid paper journal instrument")
        self._ledger = ledger
        self._key = (source_id, run_id)
        self._symbol = symbol
        self._lock = Lock()
        self._engine = PaperEngine()
        self._sequence = 0
        self._watermark = None
        self._failed = False
        with ledger._paper_event_transaction(write=True) as database:
            database.execute(
                "CREATE TABLE IF NOT EXISTS paper_streams_v1 ("
                "source_id TEXT NOT NULL, run_id TEXT NOT NULL, symbol TEXT NOT NULL, "
                "checkpoint INTEGER NOT NULL, PRIMARY KEY (source_id, run_id))"
            )
            database.execute(
                "CREATE TABLE IF NOT EXISTS paper_events_v1 ("
                "source_id TEXT NOT NULL, run_id TEXT NOT NULL, sequence INTEGER NOT NULL, "
                "event BLOB NOT NULL, ack BLOB NOT NULL, ack_sha256 TEXT NOT NULL, "
                "PRIMARY KEY (source_id, run_id, sequence))"
            )
            database.execute(
                "INSERT INTO paper_streams_v1 VALUES (?, ?, ?, 0) "
                "ON CONFLICT(source_id, run_id) DO NOTHING", (*self._key, self._symbol))
            self._checkpoint(database)
        for ack, self._watermark in self._recover(self._engine):
            self._sequence = ack["checkpoint"]

    def _apply(self, engine, event):
        stamp = _utc(event["event_time"])
        kind = event["kind"]
        with localcontext(Context(prec=28)):
            if kind == "enabled":
                engine.enabled = event["enabled"]
            elif kind == "closed_minute":
                engine.on_closed_minute(
                    self._symbol, ClosedMinute(stamp, _price(event["poc"]), event["complete"]))
            elif kind == "gap":
                engine.on_gap(self._symbol)
            else:
                fill = engine.on_trade(ExecutionTrade(self._symbol, stamp, _price(event["price"])))
                if fill is not None:
                    engine.fills.clear()  # Durable journal owns fill history.
                    return _serialize(asdict(fill))
        return None

    def _ack(self, sequence, event_raw, fill, ingested_at):
        return {
            "schema": _ACK_SCHEMA, "source_id": self._key[0], "run_id": self._key[1],
            "symbol": self._symbol, "strategy_id": _STRATEGY, "strategy_version": "1",
            "checkpoint": sequence, "event_sha256": sha256(event_raw).hexdigest(),
            "event_time": json.loads(event_raw)["event_time"],
            "ingested_at": ingested_at, "fill": fill,
            "fill_id": [*self._key, sequence] if fill is not None else None,
            "provenance": "CALLER_SUPPLIED_UNATTESTED",
            "execution_authority": False, "trading_authorized": False,
        }

    def _decode(self, sequence, event_raw, ack_raw, digest):
        try:
            if sha256(ack_raw).hexdigest() != digest:
                raise ValueError("unexpected acknowledgement digest")
            ack = json.loads(ack_raw)
            _utc(ack["ingested_at"])
            if ack != self._ack(sequence, event_raw, ack["fill"], ack["ingested_at"]):
                raise ValueError("unexpected acknowledgement identity")
        except (TypeError, ValueError, KeyError) as exc:
            raise RuntimeError("paper journal acknowledgement integrity failure") from exc
        return ack

    def _checkpoint(self, database):
        row = database.execute(
            "SELECT symbol, checkpoint FROM paper_streams_v1 WHERE source_id = ? AND run_id = ?",
            self._key).fetchone()
        if row is None:
            raise RuntimeError("paper journal checkpoint missing")
        if row[0] != self._symbol:
            raise ReplayConflict("paper journal instrument already bound")
        return row[1]

    def _recover(self, engine):
        with self._ledger._paper_event_transaction(write=False) as database:
            checkpoint = self._checkpoint(database)
            rows = database.execute(
                "SELECT sequence, event, ack, ack_sha256 FROM paper_events_v1 "
                "WHERE source_id = ? AND run_id = ? ORDER BY sequence", self._key)
            recovered = 0
            watermark = None
            for sequence, event_raw, ack_raw, digest in rows:
                if sequence != recovered + 1 or sequence > checkpoint:
                    raise RuntimeError("paper journal checkpoint gap")
                ack = self._decode(sequence, event_raw, ack_raw, digest)
                event = json.loads(event_raw)
                _validate(event)
                available = _available_at(event)
                if watermark is not None and available < watermark:
                    raise RuntimeError("paper journal event time regressed")
                if event["sequence"] != sequence or self._apply(engine, event) != ack["fill"]:
                    raise RuntimeError("paper journal execution parity failure")
                recovered = sequence
                watermark = available
                yield ack, watermark
            if recovered != checkpoint:
                raise RuntimeError("paper journal checkpoint gap")

    def read_fills(self):
        """Yield ordered committed fill ACKs; exhaust or close the snapshot."""
        for ack, _ in self._recover(PaperEngine()):
            if ack["fill"] is not None:
                yield ack

    def submit(self, event):
        _validate(event)
        raw = canonical_json(event)
        event = json.loads(raw)
        sequence = event["sequence"]
        available = _available_at(event)
        with self._lock:
            if self._failed:
                raise RuntimeError("reopen paper journal after interrupted write")
            advancing = False
            try:
                with self._ledger._paper_event_transaction(write=True) as database:
                    latest = self._checkpoint(database)
                    existing = database.execute(
                        "SELECT event, ack, ack_sha256 FROM paper_events_v1 "
                        "WHERE source_id = ? AND run_id = ? AND sequence = ?",
                        (*self._key, sequence)).fetchone()
                    if existing is not None:
                        if sequence > latest:
                            raise RuntimeError("paper journal checkpoint gap")
                        if existing[0] != raw:
                            raise ReplayConflict("paper event sequence already used")
                        return self._decode(sequence, *existing)
                    if latest != self._sequence or sequence != latest + 1:
                        raise ReplayConflict("paper journal sequence gap or stale writer")
                    if self._watermark is not None and available < self._watermark:
                        raise ValueError("paper journal event time regressed")
                    if event.get("enabled", self._engine.enabled):
                        if not any(item.id == _STRATEGY and item.version == "1"
                                   and item.enabled and item.implementation is PaperEngine
                                   for item in STRATEGIES.discover()):
                            raise ValueError("paper strategy not registered or disabled")
                    advancing = True
                    fill = self._apply(self._engine, event)
                    ack = self._ack(sequence, raw, fill, datetime.now(timezone.utc).isoformat())
                    encoded_ack = canonical_json(ack)
                    database.execute("INSERT INTO paper_events_v1 VALUES (?, ?, ?, ?, ?, ?)",
                                     (*self._key, sequence, raw, encoded_ack,
                                      sha256(encoded_ack).hexdigest()))
                    database.execute(
                        "UPDATE paper_streams_v1 SET checkpoint = ? "
                        "WHERE source_id = ? AND run_id = ?", (sequence, *self._key))
                self._sequence = sequence
                self._watermark = available
                return ack
            except BaseException:
                self._failed = advancing
                raise

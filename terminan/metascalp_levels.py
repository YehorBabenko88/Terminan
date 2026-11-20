"""MetaScalp level ownership and publication gates migrated from Meta Analyse.

This module is a pure terminal boundary within the existing Terminan
application, not another service/client. No Metasc alp API requests, broker
orders, PostgreSQL writes or numerical level computation.
Original source: meta_analyse@b49505da42a274f7232fabe5d847c91f7218a0ce
  src/meta_analyse/level_sync.py
  src/meta_analyse/level_publish.py
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256

PREFIX = "terminan:"  # Historical annotations require explicit reviewed migration.


def signature(symbol, level):
    """Stable canonical owner signature; do not rename existing user-owned annotations."""
    raw = (
        f"{symbol}|{level.timeframe}|{level.kind}|"
        f"{level.source_start.isoformat()}|{level.price}"
    )
    return sha256(raw.encode()).hexdigest()[:24]


def owned_id(row):
    """Only Terminan-created, clearly marked terminal levels are eligible."""
    if not isinstance(row, dict):
        return None
    note = str(row.get("note") or row.get("Note") or "")
    if not note.startswith(PREFIX):
        return None
    value = row.get("id", row.get("Id"))
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_rows(response):
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        keys = [key for key in ("items", "list", "levels", "data") if key in response]
        if len(keys) == 1 and isinstance(response[keys[0]], list):
            return response[keys[0]]
    raise ValueError("Unknown MetaScalp levels response; refusing destructive synchronization")


@dataclass(frozen=True)
class LevelPublication:
    allowed: bool
    reason: str
    count: int


def publication_decision(
    report, *, connection_verified: bool,
    instrument_verified: bool, max_levels: int = 500,
):
    """Source-compatible gate: never publish unverified levels."""
    if connection_verified is not True:
        return LevelPublication(False, "terminal connection not verified", 0)
    if instrument_verified is not True:
        return LevelPublication(False, "instrument mapping not verified", 0)
    if getattr(report, "verified", None) is not True:
        return LevelPublication(False, report.reason, 0)
    if type(max_levels) is not int or not 0 <= max_levels <= 500 or not isinstance(report.levels, (tuple, list)):
        return LevelPublication(False, "invalid publication limits", 0)
    if len(report.levels) > max_levels:
        return LevelPublication(False, "too many levels; explicit filtering required", 0)
    if any(not isinstance(getattr(level, "price", None), Decimal)
           or not level.price.is_finite() or level.price <= 0 for level in report.levels):
        return LevelPublication(False, "invalid level price", 0)
    return LevelPublication(
        True, "verified; publication may proceed with ownership checks",
        len(report.levels),
    )


def crossed_owned_ids(rows, previous, current, *, contiguous=False,
                      source=None):
    """Safe read-only selection: never infer a crossing over gaps or stale feeds.

    Returns owned MetaScalp row IDs *eligible for review*, not deletions.
    No network call, terminal mutation, or automatic action is performed.
    """
    if not contiguous or source != "exchange_execution":
        return ()
    try:
        previous, current = Decimal(str(previous)), Decimal(str(current))
        if not (previous.is_finite() and current.is_finite()
                and previous > 0 and current > 0):
            return ()
    except (TypeError, InvalidOperation, ValueError):
        return ()
    found = []
    for row in parse_rows(rows):
        ident = owned_id(row)
        if ident is None:
            continue
        try:
            price = Decimal(str(row.get("price", row.get("Price"))))
        except (TypeError, InvalidOperation, ValueError):
            raise ValueError("Unknown level price; refusing to guess")
        if not price.is_finite() or price <= 0:
            raise ValueError("Unknown level price; refusing to guess")
        if min(previous, current) <= price <= max(previous, current):
            found.append(ident)
    return tuple(found)

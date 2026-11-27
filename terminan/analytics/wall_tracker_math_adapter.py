"""Explicit, fail-closed Terminan consumer seam for H-owned canonical Math.

Opt-in only. The existing observational WallTracker remains untouched until
H original Meta parity, canonical Math wheel identity, independent CI, and
MASTER integration gates are proven. No second numeric kernel, provider,
SQLite connection, trading authority, or silent local fallback is created.

Required Math candidate (NOT approved for production):
  YehorBabenko88/math PR #168 @ 0c3a97aa3f76908c464298c345108bd355af4854
  python/market_math_wall_tracker.py Git blob:
  0e22810943294a8cf8163660b08b44a4cc54f9ed
"""
from __future__ import annotations

from importlib import import_module


def canonical_wall_tracker(*, min_notional="100000", max_age_ms=3000):
    """Construct the Math-owned observation lifecycle, never the local copy.

    This explicit factory is a *candidate integration interface*; it does not
    select a runtime source automatically. The caller must install the
    independently verified Math wheel first. An absent/incompatible wheel is
    a hard failure, never a downgrade to an unpinned local implementation.
    """
    try:
        owner = import_module("market_math_wall_tracker")
    except ImportError as exc:
        raise RuntimeError("PINNED_MATH_WALL_TRACKER_REQUIRED") from exc
    if (getattr(owner, "WallTracker", None) is None
            or getattr(owner, "WallObservation", None) is None):
        raise RuntimeError("PINNED_MATH_WALL_TRACKER_CONTRACT_REQUIRED")
    return owner.WallTracker(min_notional=min_notional, max_age_ms=max_age_ms)

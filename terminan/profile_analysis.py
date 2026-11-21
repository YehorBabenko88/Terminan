"""Declared profile analysis via Math; no storage, subscriptions or authority.

Candle typical prices and all aggregation/value-area arithmetic belong to Math.
These summaries describe caller-declared observations, never authenticated trade
coverage or point-in-time availability. Candle proxies remain explicitly marked.
"""
from market_math import (ValueAreaMetrics,trade_value_area_metrics,
                         candle_proxy_value_area_metrics)
from .entry_context import ProfileSummary,ProfileKind


def _summary(metrics,kind,basis):
    if type(metrics) is not ValueAreaMetrics or metrics.basis!=basis:
        raise ValueError('MATH_VALUE_AREA_RESULT_REQUIRED')
    return ProfileSummary(poc=metrics.poc,value_area_high=metrics.value_area_high,
        value_area_low=metrics.value_area_low,available_at_ms=metrics.available_at_ms,
        kind=kind,value_area_width=metrics.value_area_width)


def analyze_trade_profile(rows,*,decision_ms):
    """Analyze explicitly timed declared executed-trade price/volume bins."""
    metrics=trade_value_area_metrics(rows,decision_ms=decision_ms)
    return _summary(metrics,ProfileKind.TRADE_DISTRIBUTION,'EXECUTED_TRADE_PRICE_BINS')


def analyze_candle_proxy_profile(rows,*,decision_ms):
    """Analyze the approximate candle-typical-price proxy, never true trade POC."""
    metrics=candle_proxy_value_area_metrics(rows,decision_ms=decision_ms)
    return _summary(metrics,ProfileKind.CANDLE_PROXY,'CANDLE_TYPICAL_PRICE_PROXY')

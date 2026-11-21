"""Bounded best-bid/ask and nearby liquidity summaries for a trader UI."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from .liquidity import large_levels
from market_math import book_summary_metrics

@dataclass(frozen=True)
class BookSummary:
    symbol: str
    best_bid: Decimal | None
    best_ask: Decimal | None
    spread_ticks: Decimal | None
    bid_notional: Decimal
    ask_notional: Decimal
    largest_nearby: tuple
    valid: bool

def summarize_book(book,tick_size,level_price=None,*,max_walls=3):
    if tick_size<=0 or max_walls<0:
        raise ValueError("invalid book summary settings")
    if not book.valid or not book.bids or not book.asks:
        return BookSummary(book.symbol,None,None,None,Decimal(0),Decimal(0),(),False)
    if max(book.bids)>=min(book.asks):
        return BookSummary(book.symbol,None,None,None,Decimal(0),Decimal(0),(),False)
    bid,ask,spread,bid_notional,ask_notional=book_summary_metrics(book.bids,book.asks,tick_size)
    if bid is None or ask is None:
        return BookSummary(book.symbol,None,None,None,Decimal(0),Decimal(0),(),False)
    walls=large_levels(book,level_price,tick_size) if level_price is not None else []
    return BookSummary(book.symbol,bid,ask,spread,bid_notional,
                       ask_notional,tuple(walls[:max_walls]),True)

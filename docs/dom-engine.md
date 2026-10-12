# Independent DOM engine — first iteration

The `terminan.dom` module is an offline-only, Python 3.11+ order-book reference engine.
It does **not** import CScalp binaries, trade, subscribe to Bybit, or read credentials.

## Contracts

* Prices are nonnegative integer ticks, quantities nonnegative integer lots; the upstream
  feed adapter must validate tick/lot precision before producing `Level`.
* A `Snapshot(epoch, sequence, levels)` replaces both sides. Each delta
  `Delta(epoch, sequence, previous_sequence, levels)` contains absolute quantities.
* One writer per instrument. On a gap or epoch mismatch, mark the book `GAP`,
  preserve the last coherent state, and require a fresh snapshot.
* Zero quantity removes the level. Duplicate sequence never increments version.
  Invalid batches raise `ValueError` without changing the book.
* Bids are descending; asks are ascending. A crossed book is flagged rather than
  silently modified.
* Grouping uses explicit floor buckets; grouping precedes viewport clipping.
  The displayed grouping is a design choice, **not** a reverse-engineered CScalp formula.

## Scope and limitations

This is the deterministic model layer only. It is not wired to the HTTP server,
which deliberately has no live DOM feed. No UI scheduler, renderer, queue or
FPS throttle is implemented yet. Future integration should use a versioned
read-only adapter and must treat gaps/overflow as resynchronization events.
Do not replace `/api/logs` with fabricated live data.
Run `python -m unittest discover -s tests -v` to exercise synthetic fixtures.

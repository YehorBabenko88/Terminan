"""Read-only, synthetic-only DOM projection and fixture state.

This module deliberately never connects to an exchange or accepts order instructions.
"""
from threading import RLock
from .dom import BookEngine, Level, Snapshot, viewport


class PreviewBook:
    def __init__(self):
        self._lock = RLock()
        self._engine = BookEngine()
        self._seed()

    def _seed(self):
        levels = []
        for i in range(90):
            levels.append(Level("bid", 99999 - i, 20 + (i * 37) % 190))
            levels.append(Level("ask", 100001 + i, 20 + (i * 29) % 190))
        self._engine.snapshot(Snapshot("synthetic-preview", 1, tuple(levels)))

    def read(self, rows=25, width=1):
        if type(rows) is not int or rows not in (15, 25, 35):
            raise ValueError("rows must be 15, 25 or 35")
        if type(width) is not int or width not in (1, 5, 10):
            raise ValueError("width must be 1, 5 or 10")
        with self._lock:
            view = self._engine.view
        anchor = (100000 // width) * width
        top = anchor + (rows // 2) * width
        return {
            "source": "SYNTHETIC_FIXTURE",
            "tradable": False,
            "status": view.status.value,
            "sequence": view.sequence,
            "version": view.version,
            "rows": viewport(view, top, rows, width),
        }


preview_book = PreviewBook()

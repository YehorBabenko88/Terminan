# DOM stream bridge — iteration 2

The pure Python `BoundedFeed` queue connects a future versioned feed adapter to
the independent `BookEngine`. No exchange socket, HTTP endpoint or live order
submission is included.

* A single consumer drains FIFO events, preserving per-symbol order.
* Queue overflow drops pending events, invalidates affected books, and requires a
  new snapshot for each affected symbol. This is intentionally fail-closed.
* `FrameGate` coalesces unchanged versions and limits render cadence based on a
  caller-supplied monotonic clock. It is not a renderer or browser animation loop.
* These components are synthetic-testable and independent of the reverse-engineered
  CScalp binary.

Next: versioned feed contract, actual browser rendering, and adapter health metrics.

# Research presenter: retain the canonical basis-point policy

Base Term120 042b075dda0fc8cf6bb829d758632cfa989e8e55. ResearchService.configure_paper previously reconstructed a fraction-valued engine.slippage attribute removed by the canonical PaperEngine transfer. Valid mapping-based rule updates therefore raised AttributeError. It now forwards the existing engine.slippage_bps directly to the candidate validator. No legacy alias/property, multiplication or second execution engine is added.

The existing live engine object, notional, slippage_bps, position/reference/fill/time state, enabled flag and publish scheduling remain unchanged during valid rule updates; only the three permitted rules are committed after the candidate PaperEngine validates all parameters. Unknown/invalid rules and open-position updates refuse without changing engine state. enable=True remains failclosed; enable=False retains its existing immediate disable semantics.

Five focused public-service coroutine tests failed on the old source in both Python3.11/3.12 and pass after this one-line change. They include full/partial valid policy, invalid atomic refusal, existing-position/enable rejection and disable/empty-update behavior. One unchanged existing historical orderflow presenter test also passes in the six-case scoped source run. The coroutine runner uses send(None), creates no event loop or Qt widget, denies sockets/children/ctypes/SQLite and checks fresh CLI-X cache custody before/after. Existing async publication/close methods are unchanged.

This focused service fix does not by itself qualify Qt GUI actions or fix every adjacent adapter. Read-only audit also found desktop.update_rules currently submits a positional tuple while configure_paper expects a named mapping; that separate active GUI mismatch is reported to the parent owner, not concealed as a fullGUI PASS.

No server, provider, native/GUI/thread/process, user DB or production operation was run. No admission or authority changes. Source-only, NO_GO.

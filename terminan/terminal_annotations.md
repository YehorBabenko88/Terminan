# External terminal annotation capability

Source port: Meta Analyse PR82 b1a4d6a41054f0040a88dc80b585380fb6b4f323.

| Original capability | Canonical implementation |
| --- | --- |
| level_quality.LevelReport / verified_levels | analytics.level_quality; explicitly supplied as_of and bounded closed M1/H1/D1 range |
| history.validate_fixed_interval coverage subset | analytics.level_quality; supplied-candle coverage only, not authentication or provider ingestion |
| level_sync.LevelSync.replace / crossed | analytics.level_sync; existing metascalp_levels signatures/publication/crossing helpers reused |
| ports.MetaScalp REST methods | external_terminal.TerminalClient with typed injected managed client |
| level_publish.publication_decision | existing metascalp_levels function; literal True and finite Decimal prices enforced |

Numerical level computation stays in Math through analytics.core. No new PaperEngine, store, provider, or legacy import alias is introduced. Existing Terminan PaperEngine remains the sole executor. Existing MarketData fingerprint admission in levels.py is unchanged.

MetaScalp is the external vendor protocol name. Its localhost ports17845..17855, ping locator, connections/combo/user-levels routes and JSON wire fields are retained. The visible annotation owner/name becomes Terminan. The level direction argument remains validated but is absent from the original vendor JSON wire shape; no unsupported wire field is invented. Old owner annotations are never adopted or deleted automatically.

TerminalClient requires an injected managed asynchronous adapter implementing TerminalHttpClient. The embedding app must disable ambient proxies and supply that adapter; there is no implicit dependency/client factory. Requests set timeout3 seconds and follow_redirects=False, response bytes capped1MiB. Network adapter exceptions must be OSError/TimeoutError (or translated by the adapter); otherwise they propagate without retry. Discovery only locates a candidate: it cannot verify a connection/instrument/source or authorize publication.

GET retries at most3 times; POST/DELETE exactly once. Cancellation propagates. Reconciliation always rereads terminal state, stages all owned/desired DTOs before mutations, refuses conflicting IDs/aliases/invalid rows, and serializes per-instrument operations. An uncertain mutation may have executed remotely: it propagates and a later explicit call rereads before deciding. This is no remote transaction or rollback guarantee.

verified_levels reports completeness only of the supplied closed requested range. The caller independently authenticates source data, connection, and instrument before invoking publication; the helper does not convert MarketData UNKNOWN quality into trust. Calendar periods are refused. Tests use fake clients only; actual external protocol/host UI, transport construction, permissions, native processes, PostgreSQL and end-to-end startup remain unqualified.

Full Candle OHLCV admission additionally delegates to Math candle_ohlcv_valid (SDK23ee76f or descendant): malformedopen/close/volume cannot become publication-eligible merely because high/low and intervalcoverage are valid. This predicate validates numericdomain only and does not authenticate source data.

# Canonical source and research responsibilities

Market Data owns exchange subscriptions, market-data persistence, capture/replay and immutable historical reads. Terminan consumes explicitly injected authenticated read capabilities; an answered endpoint or locally consistent receipt does not establish live market truth, history completeness or source authenticity. Managed readiness remains subject to Unified's current admission and private capability checks.

Terminan owns analytics, strategies, the single PaperEngine, offline replay, causal paper/account state and research import validation. Math owns numerical market/research/financial kernels. Unified owns lifecycle, source admission, infrastructure, private credentials and publication custody. No module gains live-order or production permission from these responsibilities.

## Pure historical research import

SDK API: terminan.research_import.validate_research_import(record,trusted_sources). The historical1.1 metadata record binds producer terminan, identity/revision/run/receipt and a separately provided external trust tuple. Input is bounded literal JSON. Receipt consistency and a matching external pin validate the declared historical summary; metrics/model claims are not independently recomputed here. Numeric fees/slippage shape delegates Math.

Both acceptance and refusal retain execution_authority=False, trading_authorized=False and source_capability=False; source_authenticity=NOT_EVALUATED and native=NOT_RUN. ACCEPTED_HISTORICAL is not a source, coverage, execution or trading grant. No new HTTP research-import route or Data endpoint alias is provided. Read-only Terminan capabilities advertise research_import_validation while source state remains UNAVAILABLE.

Historical record/SQLite decoders under terminan.migration preserve original archived formats for explicit operator restoration. Their legacy table names and raw snapshots are provenance, not active producer aliases, collectors or additional execution engines.

# Continuation strategy transfer

The original `volatility_expansion_entries` decision policy now lives in Terminan as `generate_continuation_signals`; numerical candle-body and bracket geometry live in Math. The result uses the existing `ResearchSignal` and `PaperEngine`, with no second executor.

Old inferred `start + bar_ms` availability is replaced by required event-end and availability clocks. Future rows are preflighted; missing or future matching volatility emits no signal. Conflicting identities refuse; eligible versions are selected by clock rather than list order. Caller declarations do not authenticate market data or authorize trading.

The Math prerequisite is currently an unpublished candidate. This transfer is not active in hosted CI until independently accepted Math is published and all consumers are source-pinned. Old Data generators and consumers remain; no legacy inventory deduction.

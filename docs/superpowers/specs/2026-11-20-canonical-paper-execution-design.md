# Canonical paper execution migration

Extend the single terminan.paper.PaperEngine. Source baseline Strattester13998cf87139330dd0406fed00acd148e045e6c4 research/execution.py; existing canonical baseline Terminan f20eef4bb3050412f1e1a72bf57f212cccdc5d22. No native services, collection, broker orders, external terminal writes or actual user databases are exercised.

## Chosen approach

The parent explicitly selected one existing engine with new signal/OHLC orchestration. Copying the192line simulator into another engine violates single ownership; leaving a forwarding shim or refusing every run does not migrate execution. Existing registry/ledger are reused. Math owns numerical kernels; Terminan owns source/time admission, signal state, policy, persistence and replay.

## Numerical boundary

Use six Math functions adverse_execution_price(price,side,bps,entry), paper_position_size(notional,entry), paper_entry_fee(notional,rate), paper_stop_price(entry,side,stop_pct), paper_entry_side(price,poc,threshold), paper_fill_metrics(side,entry,exit,size,entry_fee,fee_rate). Decimal-only bounded inputs; every intermediate uses explicit28 HALF_EVEN matching normal historical paper arithmetic, independent of caller context. Net subtracts entry fee then exit fee. Terminan stages all candidate state before commit. Historical float sizing/equity policy stays in Terminan but arithmetic moves into separately agreed Math helpers; no local numerical alias remains.

## Canonical contracts

Active strategy IDs become poc_next_minute(version2) and ohlc_signal(version1), with no accepted legacy ID alias. Active paper replay/result/event/ACK contracts become v2 where identity changes. Update every UI, journal, registry, API and test consumer. Historical v1 data is read only through an explicitly named migration boundary, never accepted by active replay. Preserve original SQLite bytes and existing receipt hashes; no implicit rewrite. Existing old stream identities cannot silently open a new active stream. Explicit restore into a separate fixture destination must prove financial/state replay and source hash preservation.

## Generic execution

New typed ResearchSignal/ResearchBar DTOs feed PaperEngine.execute_signal, not a new engine class. A bounded fully preflighted batch contains strictly ordered closed continuous OHLC bars; future/duplicate/gapped/invalid bars refuse before state or ledger writes. Market signals enter no earlier than decision time; limit signals wait one full declared bar interval. Opening-gap prices precede intrabar fills. Default SL_FIRST is conservative: a fill-bar stop remains effective, but an intrabar fill receives TP only when the bar close proves a crossing after entry. Explicit TP_FIRST is an annotated optimistic research policy. Actual tick ordering remains UNKNOWN; the source is caller-supplied/unattested. EOD closes any remaining simulated position; no invented market records.

A new bounded offline signal replay function/CLI validates source as_of and request shape, creates the existing engine, and records a completed immutable receipt in the existing PaperReplayLedger. Exact retry after process restart returns the committed receipt; changed input under the same run ID conflicts. No new database or paper ledger implementation.

## Validation and migration limits

Pin same-bar conservative/optimistic cases, pre-decision wick refusal, market/limit gaps, SL/TP/EOD, long/short/slippage/fees, invalid-late-row atomicity, hostile Decimal contexts, committed-receipt restart and historical v1 read-only export/isolated restore. All local checks are reviewed pure Python with native process/system/socket construction denied or inert dependencies. Existing forbidden native tests remain enabled but NOT_RUN. Original scale-out, learning/organism graphs and result publication remain explicitly RETAINED_UNMIGRATED until their own consumers and parity are ported; no whole-repo retirement claim.

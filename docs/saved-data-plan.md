# Saved-data workspace

Implement inline on a new branch above PR29, preserving PR27's single ladder and all R4 behavior. User explicitly requests practical implementation without extra approval stages.

1. Audit pinned Grid schema + migrations and Strattester market/result persistence. Generate a reviewed dataset catalog with hashes, primary keys, field types and explicit exclusions for operational/secret-bearing state. Test catalog provenance against source checkouts.
2. Add dormant configurable providers: fixture JSON, SQLite `mode=ro`/query_only snapshots, optional PostgreSQL18 read-only transactions. No upstream application Store constructors, migrations or real source connections. Keyset pages bind source/dataset/symbol/timeframe/cutoff/epoch; strict values, bounded responses and privacy-safe errors.
3. Add separate `/saved` workspace: historical OHLCV canvas, multiple timestamp footprint clusters/POC/delta, research run metrics and bounded generic dataset table. Never populate the synthetic ladder from historical data. Buttons, paging, replay, zoom/pan and abort previous requests.
4. Python temporary-DB/negative regressions, browser controls/cancellation regressions, exact-head Windows/Linux CI and SHA256 evidence. One final independent review; retain failures and limitations. Publish own Draft PR and Windows commands. No merge/deploy/G1/system policy/live feeds/production writes.

Ruling: use optional direct Grid PostgreSQL reads rather than the limited upstream gateway (no cursor/provenance, nullable POC conversion defect). Runtime PostgreSQL compatibility remains untested until a later authorized isolated PG18 environment; do not claim real-source acceptance. Stored book snapshots are historical rows, never live authority. Internal job/lease/control/log tables are inventoried but excluded from public payloads.

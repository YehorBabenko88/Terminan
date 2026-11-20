# Canonical terminal analytics cutover (safe-code phase)

Base Terminan #98 a88cef10a910d17b32cdcf483950be9dfa087649; Meta source #82 b1a4d6a41054f0040a88dc80b585380fb6b4f323.

1. Move selected pure analytics/DTO/presentation modules into terminan.analytics; remove Meta duplicate PaperEngine from the imported source closure and consume terminan.paper only. Domain arithmetic calls installed Math APIs.
2. Move read-only persisted-state export into terminan.migration with historical schema/digest identities retained as source records only. Rename active archive APIs/schema, provide explicit lossless fixture-tested schema migration.
3. Replace active Grid symbols/imports/env/wire/client contracts with market_data and update consumers, tests, package metadata and CLI. No facade packages or alias imports.
4. Migrate Qt view and settings into Terminan with injected read-only canonical service; no exchange collectors, DSN write owner or installer imported. Preserve unported source capabilities explicitly, block repository retirement until their migrations prove parity.
5. Run selected reviewed pure Python tests, static import/forbidden-launch scan, wheel/sdist packaging and installed imports. No PowerShell/CMD, native installer, service, firewall, production DB or original-data action.

# Frozen read-only SQLite inputs

Research UI (TERMINAN_RESULTS_DB) and explicit candle imports accept only absolute ordinary local standalone DELETE-mode snapshots, without WAL/SHM/journal sidecars or linked paths. Missing research configuration returns an empty list. A configured invalid snapshot is refused. The source must be frozen externally before configuration.

Readers use SQLite mode=ro&immutable=1, query_only and trusted_schema=OFF. Existing migration path/sidecar checks are reused; source identity, size and modification time are checked before/after reading. These checks do not authenticate provenance or guarantee safety against a concurrent hostile writer. Never point these readers at an active database. Existing restore/recovery writers are unchanged.

Regression fixture demonstrates that the previous mode=ro connection created a -shm file on an owned WAL copy. New tests cover refusal before SQLite, standalone rows, write denial, linked input and changes during projection. All database tests use newly owned temporary fixtures. Native services, user databases and network access are not exercised.

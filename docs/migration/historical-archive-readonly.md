# Historical archive read-only correction

The inherited read_snapshot path used a read/write SQLite opener. After its previously owned path was moved, reading could recreate an empty file; a present sidecar was not refused. Network/parent-alias/stream spellings now refuse lexically before filesystem access. The initial four pre-fix cases were RED (three failures and one missing API), and the added lexical-path guard reproduced three filesystem touches before refusal, using fresh private fixtures only.

ResearchArchive.read_snapshot now reuses PaperReplayLedger._existing_database, which refuses missing/foreign/linked/hot-sidecar inputs before any write or recovery. ResearchArchive.read_existing(path, source_id) exposes that reader without invoking a database constructor. No new store, receipt schema or financial evaluator is introduced; historical bytes/metrics/dispositions remain unchanged.

Five regression cases and the22 existing historical import/archive cases pass on Python3.11/3.12 with child/network/native effects denied and only owned temporary SQLite. Restore remains a fresh-destination operation through restore_frozen_research_results; retry means read the preserved archive, never overwrite/adopt an existing target.

The aggregate also pins the actual causal numerical SDK Matha5868944bf1bae813403a32b22d329c1da6f8238 and Datae1ea525273aa2181e7357ca84a774ac2fb30ced0 in CI. Python source tests install both SDKs; the full test matrix and browser obligations remain enabled. The aggregate includes Term116 all-visible-row funding gap correction on these exact SDKs. Prior Term113/114 negative counterexamples remain recorded; source and installed-artifact acceptance are rerun on the aggregate SHA. Full hosted/native/installer acceptance is still pending.

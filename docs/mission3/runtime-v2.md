# Node-local runtime dashboard

`/runtime` and `GET /api/runtime-v2` consume an explicitly configured local file:

```
TERMINAN_RUNTIME_V2_SNAPSHOT=/absolute/local/path/runtime.json
```

The file must contain `unified.runtime.v2` with API 2.0. The independent consumer validates the exact fields, six core modules, optional registered modules up to 64, compatible module versions/API majors, dependency graph, closed states/reasons, readiness aggregate and disabled physical/trading authority. Files are bounded to 256 KiB; duplicate JSON fields, nonfinite values, nonregular files and symlink/reparse paths are rejected before inspecting their descendants. Windows accepts only local fixed drives; UNC and mapped network drives are rejected before file metadata access. Native Windows validation remains pending. Missing or invalid input returns an explicit UNAVAILABLE envelope without private exception text.

The dashboard is read only. It displays local supervisor observations; Grid remains the distributed fleet authority. CPU, memory, database health and node authentication are UNKNOWN. Source authenticity is UNVERIFIED, physical acceptance NOT_RUN and physical deployment forbidden. Existing v1 infrastructure, lab, terminal and saved-source contracts remain separate.

Focused verification: `python -m unittest tests.test_runtime_v2 -v`.
For a local HTTP fixture, run `tests/check_runtime_v2.cjs` with `RUNTIME_TEST_URL` and an installed Playwright dependency (`RUNTIME_PLAYWRIGHT` may provide its absolute module path). Chromium verification uses an ephemeral loopback server and no office services or databases.

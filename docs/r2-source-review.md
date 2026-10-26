# R2 source audit and dispositions

Audited base: frozen PR #9 at 0ad0f36edce2ac7717c753d35ebe113dc6334fd0.
Independent reviewer read all application Python modules, both shipped HTML UIs,
source contract/lock, runners, evidence code and relevant tests. Main refs were
freshly rechecked; Issue #6 now contains physical observations for old main only.
Those observations do not establish G0 RC or R2 physical PASS.

| Area | Finding at G0 base | R2 disposition / regression |
|---|---|---|
| DOM | Retired snapshots ignored but retired deltas poison current epoch | Ignore retired delta; test preserves new view unchanged |
| DOM grouping | Nonaligned top105 / width10 hides liquidity grouped at100 | Align top to anchor; explicit regression |
| Chart | No zoom/pan/reset, resize/DPR observer or inspection | Dedicated canvas preview, timestamp x mapping, bounded viewport, pointer/controls, OHLCV inspection |
| Chart time | Row-index x compresses gaps; levels can appear before confirmed_ms | R2 uses UTC-proportional positions and only available bars; no speculative level overlay |
| UX | Header changes before old panels clear | Clear all panels at generation start; identity binds every committed frame |
| Cancellation | G0 generation fencing does not create replay pipeline | R2 aborts superseded requests, suppresses stale generations, bounds deadlines |
| Footprint | Flat mixed-minute list, no UI timestamp/POC; bounded DB limit can truncate levels | R2 displays one complete generated closed minute, UTC and deterministic POC; legacy limit coverage explicitly unknown/PARTIAL |
| Footprint contract | Duplicate price levels and invalid volume/delta accepted | Reject duplicate/arithmetic/NaN; test NULL POC separately |
| Future data | Complete source candle accepted before period close | Reject early completed candle; R2 partial OHLC contains only observed virtual path |
| POC observations | Incomplete candle produces close event | Exclude incomplete; optional as_of and available_at contract |
| Grid coverage | Requested1h used despite fixed1m identity | Compute actual source period |
| API | No synthetic replay dispatch; legacy routes may access configured DB | Dedicated R2Handler never delegates legacy routes; request tests monkeypatch DB calls to fail |
| Evidence | Hashes + summary alone can pass G0 integrity helper | R2 requires smoke/ready/checklist or full browser assertions/metrics/screenshots and exact clean SHA |
| Performance | No browser CPU/cadence/heap/idle acceptance | Render avg/p95, idle RAF, replay cadence, Chromium CPU/GC heap and structural disposal gates |

Independent implementation review at 630b386ed2462a89cf7069db6652b2dc8d36e73e
confirmed: Promise.all sibling leak after partial HTTP failure; research dataset
prefix checking rather than exact identity; missing CPU/cadence acceptance.
All reproduced RED then fixed. Closed footprint availability and report-level
runner-error acceptance were also tightened. Added pending-request disposal
regression; no retry/skip converts failures to PASS.

Scope boundaries: original G0 UI/launcher remain available for regression and
rollback, but are not the R2 preview entrypoint. Original prototype renderer from
other branches is not imported. R2 supplies its own small demand-driven browser
frame pipeline, not an unverified bulk merge of that prototype.

Not implemented: live L2/exchange subscriptions, true executed trade tape, order
entry, connected DB operations, research execution/fills, production deployment.
Research fixtures carry no authority. Higher-timeframe level/trade overlays are
deferred until their availability/dataset contract is explicit; R2 does not invent
them. These are scope limits, not prerequisites on running Grid/Strattester.

Measured headless bounds do not prove all future workloads leak-free, physical
display FPS or total machine CPU/RSS. Firefox lacks CDP heap/TaskDuration metrics;
cadence/render/idle/lifecycle checks still run and unsupported metrics are explicit.

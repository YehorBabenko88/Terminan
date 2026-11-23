# Rich entries implementation plan

Goal: preserve selection metadata end-to-end without a second selection/execution owner. Architecture: continuation core -> ResearchEntry v2; exact snapshot admission -> existing signal evaluator/Paper -> typed entry/outcome association. Tech: Python311/312 stdlib and pinnedMath420. Spec:rich-entry-design.md.

Global constraints: no old public alias, no lost metadata/None coercion, no authority, no Root/Data source changes, fixed pins, historical archives unchanged.

Review focus: hostile nested keys/metaclass leaves refuse without callbacks; caller mutation during first numeric callback cannot change any later entry; duplicate clock association refuses before eval; later volatility revisions preserve earlier entry prefixes; unknown evidence never becomes observed zero.

- [ ] Write failing rich continuation/evaluation tests proving metadata, wrappers, v2catalog and retiredAPI behavior; run RED with reviewed inert runner.
- [ ] Refactor continuation into single rich selector; extend evidence v2 using actual detached volatility DTOs; migrate all active callers preserving test names/oracles; run focused GREEN.
- [ ] Implement bounded exact rich snapshot/admission and typed entry evaluation via existing evaluator once; test all dispositions, mutation/foreign/oversize/clock refusals, metadata fingerprints and no authority; GREEN.
- [ ] Update mandatory installed checker with only new test selectors, preserving every original255 selector; add source provenance and exact runtime census.
- [ ] Build actual wheel using reviewed inert archive packaging (no installer/subprocess insidePython), verify rawGit/source/RECORD, source/wheel fresh-cache scoped suites bothPy plus installed mandatory tests, privateSQL only. Preserve all held tests. Commit private candidate, receipt and independentQA handoff; no publication.

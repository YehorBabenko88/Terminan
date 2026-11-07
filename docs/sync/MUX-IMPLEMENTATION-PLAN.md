# Review4 browser adapter implementation plan

Goal: executable browser-safe C3 decoding and bounded transport components for the separately versioned Control Mux profile. Frozen Sync v1 remains unchanged.

Implementation checkout: existing feature/terminan-sync-v1-20261106, base HEAD 42686cd8fafcefaed3c5df5adaee5173d27543fd. Ownership remains terminan/sync/**, tests/sync/**, docs/sync/** and own workflow. Review4 dependency published in unified-system 360c5cdc9dae88416d69f8765f3dff5ab8828945; profile SHA256 335cda8e5d451fd9ab90586b6f6a4d6fbaf5f52eabb5a11762d9100ed92fefdf.

1. Write failing codec tests, then implement terminan/sync/c3.js. Accept raw canonical ASCII text only, never arbitrary host object graphs. Enforce bytes, containers, keys, members, arrays, strings, node budget and numeric ban during parsing. Return opaque branded tokens and immutable detached values. Test review4 vectors, hostile host objects and browser execution.
2. Implement bounded exact SSE record decoding with tests for arbitrary byte fragmentation, reconnect boundaries, noncanonical records and oversize buffers. This is framing only: no authority or domain admission.
3. Coordinate actual HTTP paths, authentication context, command/session response validation and stream attachment with A2 and ROOT. Do not invent endpoints or credentials; no production mock adapter. Implement executable HTTP/session/command adapter after exact contracts are available.
4. Verify original contract suite and new browser components. Update dependency matrix and evidence; distinguish local preliminary checks from endpoint, Windows and physical acceptance.

No domain data is admitted by C3 validity. Unknown domains remain UNAVAILABLE. No C3 stream is connected to the v1 reducer, and no component grants authority or changes backend state by default.

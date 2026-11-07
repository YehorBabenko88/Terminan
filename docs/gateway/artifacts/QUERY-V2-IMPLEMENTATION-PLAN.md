# Query v2 chart implementation plan

ROOT scoped local design ACK: QUERY-V2-CHART-DESIGN.md SHA256
9717e9bd1917dcfd833854d484d6a3f94bfd47abdac6f4f89b293780ff6fb42a.
Implementation base8eef; design-only80929c. Execute inline within four owned scopes.

1. Copy exact committed1610 packet + schemas into new v2 fixture directory.
   RED new scenarios preserve all original27 IDs: actual2markers, five preflight,
   raw hashes/typed joins/result metadata, six integral columns, full clock/source
   identity, missing/reset, v1/v2 mutual rejection and cross-API stale success/failure.
2. Add distinct renderQueryComputedLevels. Share only validated inert presentation;
   do not mutate/relabel/drop v2 into v1. Strict closed schema + semantic lineage,
   input rows and Meta payload/digest joins. All-integral ASCII subset permits
   exact existing Meta digest preimage serialization; no new C3/transport codec.
3. Update mandatory source-bound inventory/owned workflow for new branch/base8eef.
   New source qualification + actual Chromium v2 stand; repeat v1/metadata display
   on new source without transferring old evidence. Evidence stays outside source.
4. Independent review, fix actual issues with RED regression, exact final HEAD/tree,
   update DraftPR72 and dependency report. No runtime/job/store/auth/Sync effects.

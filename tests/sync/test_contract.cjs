const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const F = require("./fixtures.cjs");
const protocolPath = path.join(__dirname, "../../terminan/sync/protocol.js");
const P = fs.existsSync(protocolPath) ? require(protocolPath) : {};
function ready() {
  assert.equal(typeof P.SyncState, "function", "SyncState consumer must exist");
  const clock = F.clock();
  const s = new P.SyncState({
    clock: () => clock.now(),
    validateDomain: () => true,
  });
  s.install(F.snapshot());
  s.connection(true);
  return { s, clock };
}
const altered = (x, f) => (f(x), x);
test("snapshot_consistency", () => {
  const { s } = ready();
  assert.throws(() =>
    s.install(
      altered(
        F.snapshot(),
        (x) => (x.resources[0].cluster_generation = "other"),
      ),
    ),
  );
  assert.equal(s.revision, 5);
  assert.notEqual(s.status, "LIVE");
});
test("missing_event", () => {
  const { s } = ready();
  s.apply(altered(F.event(), (x) => (x.event_sequence = 12)));
  assert.equal(s.status, "RESYNCING");
  assert.equal(s.revision, 5);
});
test("duplicate_event", () => {
  const { s } = ready();
  s.apply(F.event());
  s.apply(F.event());
  assert.equal(s.revision, 6);
  assert.equal(s.cursor, "fixture-c11");
  assert.equal(s.status, "LIVE");
});
test("conflicting_duplicate", () => {
  const { s } = ready();
  s.apply(F.event());
  s.apply(
    altered(F.event(), (x) => (x.payload.upserts[0].value.progress = 99)),
  );
  assert.equal(s.status, "RESYNCING");
  assert.equal(s.resources.get("fixture-job").value.progress, 20);
});
test("out_of_order", () => {
  const { s } = ready();
  s.apply(altered(F.event(), (x) => (x.event_sequence = 12)));
  s.apply(F.event());
  assert.equal(s.revision, 5);
  assert.equal(s.status, "RESYNCING");
});
test("generation_change", () => {
  const { s } = ready();
  s.apply(altered(F.event(), (x) => (x.cluster_generation = "fixture-g2")));
  s.apply(F.event());
  assert.equal(s.status, "RESYNCING");
  assert.equal(s.revision, 5);
});
test("expired_cursor", () => {
  const { s } = ready();
  s.error({ code: "RESYNC_REQUIRED", reason: "CURSOR_EXPIRED" });
  assert.equal(s.status, "RESYNCING");
  assert.equal(s.resumeCursor, null);
});
test("resync_required", () => {
  const { s } = ready();
  s.error({ code: "RESYNC_REQUIRED" });
  s.install(F.snapshot());
  s.connection(true);
  assert.equal(s.cursor, "fixture-c10");
  assert.equal(s.status, "LIVE");
});
test("stale_authority", () => {
  const { s, clock } = ready();
  clock.advance(15001);
  s.tick();
  assert.equal(s.status, "STALE");
  assert.equal(s.canMutate, false);
});
test("unauthorized", () => {
  const { s } = ready();
  s.error({ code: "FORBIDDEN" });
  assert.equal(s.resources.size, 0);
  assert.equal(s.canMutate, false);
  assert.throws(() => s.command({ operation: "uninstall" }), /UNAVAILABLE/);
});
test("expired_session", () => {
  const { s } = ready();
  s.error({ code: "SESSION_EXPIRED" });
  s.apply(F.event());
  assert.equal(s.status, "AUTH_REQUIRED");
  assert.equal(s.resources.size, 0);
});
test("multiple_clients", () => {
  const a = ready(),
    b = ready();
  a.s.apply(F.event());
  assert.equal(b.s.revision, 5);
  b.s.apply(F.event());
  assert.equal(a.s.revision, b.s.revision);
  assert.deepEqual([...a.s.resources], [...b.s.resources]);
});
test("leader_failover", () => {
  const { s } = ready();
  s.connection(false);
  assert.equal(s.status, "RECONNECTING");
  assert.equal(s.resumeCursor, "fixture-c10");
  s.connection(true);
  s.apply(F.event());
  assert.equal(s.revision, 6);
  assert.equal(s.status, "LIVE");
});
test("relocation_PC1_LS7", () => {
  const pc1 = ready();
  pc1.s.stop();
  const ls7 = ready();
  assert.equal(ls7.s.resources.get("fixture-job").resource_id, "fixture-job");
  assert.equal(ls7.s.revision, 5);
  assert.equal(pc1.s.status, "OFFLINE");
});
test("jobs_after_shutdown", () => {
  const pc1 = ready();
  pc1.s.stop();
  const ls7 = ready();
  ls7.s.apply(F.event());
  assert.equal(ls7.s.resources.get("fixture-job").value.progress, 20);
  assert.equal(pc1.s.revision, 5);
});
test("dataset_metadata", () => {
  const { s } = ready();
  const e = altered(F.event(), (x) => {
    x.type = "DATASET_CHANGED";
    x.sequence_scope = "DATASET";
    x.dataset_id = "fixture-dataset";
    x.stream_id = "fixture-dataset-stream";
  });
  assert.equal(s.apply(e), "RESYNC_REQUIRED");
  assert.equal(s.revision, 5);
});
test("buffer_overflow", () => {
  const { s } = ready();
  s.error({ code: "RESYNC_REQUIRED", reason: "BUFFER_OVERFLOW" });
  assert.equal(s.resumeCursor, null);
  assert.equal(s.status, "RESYNCING");
});
test("clock_rollback", () => {
  const { s, clock } = ready();
  clock.mono = 16000;
  clock.wall -= 300000;
  s.tick();
  assert.equal(s.status, "STALE");
});
test("scope_change", () => {
  const { s } = ready();
  s.error({ code: "FORBIDDEN" });
  assert.equal(s.cursor, null);
  assert.equal(s.resources.size, 0);
});
test("no_quorum", () => {
  const { s } = ready();
  s.connection(false);
  assert.notEqual(s.status, "NO_QUORUM");
  s.install(
    altered(F.snapshot(), (x) => (x.authority_status.state = "NO_QUORUM")),
  );
  s.connection(true);
  assert.equal(s.status, "NO_QUORUM");
});
test("payload_limits", () => {
  ready();
  assert.throws(() => P.parseBounded('{"a":1,"a":2}', "event"));
  assert.throws(() => P.parseBounded('{"a":1e999}', "event"));
  assert.throws(() => P.parseBounded(" ".repeat(65537), "event"));
  const { s } = ready();
  assert.throws(() =>
    s.install(altered(F.snapshot(), (x) => (x.unexpected = true))),
  );
});
test("four_dimensions", () => {
  ready();
  const x = P.integrityDimensions({
    byte_integrity: { state: "VERIFIED" },
    source_completeness: { state: "GAPS" },
    redundancy: { state: "UNDER_REPLICATED" },
    authority_freshness: { state: "STALE" },
  });
  assert.deepEqual(
    x.map((v) => v.state),
    ["VERIFIED", "GAPS", "UNDER_REPLICATED", "STALE"],
  );
  assert.deepEqual(
    P.integrityDimensions({}).map((v) => v.state),
    ["UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN"],
  );
});
test("dataset_snapshot_anchor", () => {
  const { s } = ready();
  assert.throws(() =>
    s.install(
      altered(F.snapshot(), (x) => {
        x.snapshot_scope = "DATASET";
        x.dataset_id = "fixture-d";
        x.dataset_revision = null;
      }),
    ),
  );
  assert.equal(s.revision, 5);
});
test("authority_renewal", () => {
  const { s } = ready();
  const e = altered(F.event(), (x) => {
    x.type = "HEARTBEAT";
    x.revision = 5;
    x.metadata_revision = 5;
    x.payload = { upserts: [], deletes: [] };
    x.authority_status.state = "NO_QUORUM";
  });
  s.apply(e);
  assert.equal(s.status, "NO_QUORUM");
  assert.equal(s.revision, 5);
});
test("combined_change_limit", () => {
  const { s } = ready();
  const e = F.event();
  e.payload.upserts = Array.from({ length: 100 }, (_, i) => ({
    ...F.resource(),
    resource_id: "fixture-" + i,
    metadata_revision: 6,
  }));
  e.payload.deletes = ["fixture-job"];
  s.apply(e);
  assert.equal(s.status, "RESYNCING");
  assert.equal(s.revision, 5);
  assert.throws(() =>
    s.install(
      altered(
        F.snapshot(),
        (x) => (x.control_stream.retention_window.minimum_seconds = 599),
      ),
    ),
  );
});

test("dataset authority loss immediately removes global LIVE", () => {
  const { s } = ready();
  s.install(F.controlWithDataset());
  s.connection(true);
  s.install(F.datasetSnapshot());
  const e = F.datasetHeartbeat();
  e.authority_status.state = "NO_QUORUM";
  s.apply(e);
  assert.equal(s.status, "NO_QUORUM");
  assert.equal(s.canMutate, false);
});
test("snapshot resource bound applies to incremental growth", () => {
  const { s } = ready();
  let x = F.snapshot();
  x.resources = Array.from({ length: 1000 }, (_, i) => ({
    ...F.resource(),
    resource_id: "fixture-" + i,
  }));
  s.install(x);
  s.connection(true);
  s.apply(F.event());
  assert.equal(s.status, "RESYNCING");
  assert.equal(s.resources.size, 1000);
});

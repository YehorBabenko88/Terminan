const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const F = require("./fixtures.cjs");
const target = path.join(__dirname, "../../terminan/sync/client.js");
const M = fs.existsSync(target) ? require(target) : {};
function setup(adapter) {
  assert.equal(typeof M.SyncClient, "function", "SyncClient must exist");
  const clock = F.clock();
  const client = new M.SyncClient({
    adapter,
    clock: () => clock.now(),
    random: () => 0,
    validateDomain: () => true,
  });
  return { client, clock };
}
function transport() {
  let onEvent, onError;
  const calls = [];
  return {
    calls,
    getSnapshot: async () => F.snapshot(),
    subscribe: (options) => {
      calls.push(options.cursor);
      onEvent = options.onEvent;
      onError = options.onError;
      return () => {};
    },
    event: (e) => onEvent(e),
    error: (e) => onError(e),
  };
}
test("absent approved endpoint remains UNAVAILABLE without fetching", async () => {
  const { client } = setup();
  await client.start();
  assert.equal(client.state.status, "UNAVAILABLE");
  assert.equal(client.state.canMutate, false);
});
test("client resumes last applied cursor after leader failover", async () => {
  const a = transport(),
    { client, clock } = setup(a);
  await client.start();
  a.event(F.event());
  await client.flush();
  a.error({ code: "UNAVAILABLE" });
  clock.advance(1000);
  await client.tick();
  assert.deepEqual(a.calls, ["fixture-c10", "fixture-c11"]);
  assert.equal(client.state.revision, 6);
  client.stop();
});
test("client gap discards cursor then gets coherent snapshot", async () => {
  const a = transport(),
    { client, clock } = setup(a);
  await client.start();
  a.event({ ...F.event(), event_sequence: 12 });
  await client.flush();
  assert.equal(client.state.status, "RESYNCING");
  clock.advance(1000);
  await client.tick();
  assert.deepEqual(a.calls, ["fixture-c10", "fixture-c10"]);
  assert.equal(client.state.revision, 5);
  client.stop();
});
test("expired session stops retries and clears data", async () => {
  const a = transport(),
    { client, clock } = setup(a);
  await client.start();
  a.error({ code: "SESSION_EXPIRED" });
  clock.advance(60000);
  await client.tick();
  assert.equal(a.calls.length, 1);
  assert.equal(client.state.status, "AUTH_REQUIRED");
  assert.equal(client.state.resources.size, 0);
  client.stop();
});
test("late snapshot after UI shutdown cannot change client", async () => {
  let resolve;
  const a = transport();
  a.getSnapshot = () => new Promise((r) => (resolve = r));
  const { client } = setup(a);
  const pending = client.start();
  client.stop();
  resolve(F.snapshot());
  await pending;
  assert.equal(client.state.status, "OFFLINE");
  assert.equal(client.state.revision, null);
  assert.equal(a.calls.length, 0);
});
test("client bounded queue rejects actual overflow", async () => {
  const a = transport(),
    { client } = setup(a);
  await client.start();
  for (let i = 0; i < 257; i++) a.event(F.event());
  await client.flush();
  assert.equal(client.state.status, "RESYNCING");
  assert.equal(client.state.revision, 5);
  client.stop();
});
test("concurrent clients remain independent and relocation uses new snapshot", async () => {
  const a = transport(),
    b = transport(),
    ca = setup(a).client,
    cb = setup(b).client;
  await Promise.all([ca.start(), cb.start()]);
  a.event(F.event());
  await ca.flush();
  assert.equal(cb.state.revision, 5);
  b.event(F.event());
  await cb.flush();
  assert.equal(ca.state.revision, cb.state.revision);
  ca.stop();
  assert.equal(cb.state.status, "LIVE");
  cb.stop();
});
test("reconnect floor and rolling rate cap prevent retry storm", async () => {
  const a = transport();
  a.getSnapshot = async () => {
    throw { code: "UNAVAILABLE" };
  };
  const { client, clock } = setup(a);
  await client.start();
  for (let i = 0; i < 10; i++) {
    clock.advance(1000);
    await client.tick();
  }
  assert.ok(client.attempts.length <= 6);
  client.stop();
});

test("dataset session expiry clears all privileged state", async () => {
  const a = transport();
  let failDataset;
  a.getSnapshot = async () => F.controlWithDataset();
  a.getDatasetSnapshot = async () => F.datasetSnapshot();
  a.subscribeDataset = (o) => {
    failDataset = o.onError;
    return () => {};
  };
  const { client } = setup(a);
  await client.start();
  await client.subscribeDataset("fixture-d");
  failDataset({ code: "SESSION_EXPIRED" });
  assert.equal(client.state.status, "AUTH_REQUIRED");
  assert.equal(client.state.resources.size, 0);
  client.stop();
});
test("dataset future metadata waits then applies at exact control barrier", async () => {
  const a = transport();
  let datasetEvent;
  a.getSnapshot = async () => F.controlWithDataset();
  a.getDatasetSnapshot = async () => F.datasetSnapshot();
  a.subscribeDataset = (o) => {
    datasetEvent = o.onEvent;
    return () => {};
  };
  const { client } = setup(a);
  await client.start();
  await client.subscribeDataset("fixture-d");
  const e = F.datasetHeartbeat();
  e.metadata_revision = 6;
  datasetEvent(e);
  await client.flush();
  assert.equal(client.state.datasets.get("fixture-d-stream").sequence, 20);
  a.event(F.event());
  await client.flush();
  assert.equal(client.state.datasets.get("fixture-d-stream").sequence, 21);
  assert.equal(client.state.revision, 6);
  client.stop();
});

test("dataset stream reconnect resumes through a fresh metadata snapshot", async () => {
  const a = transport();
  let error,
    subscriptions = 0;
  a.getSnapshot = async () => F.controlWithDataset();
  a.getDatasetSnapshot = async () => F.datasetSnapshot();
  a.subscribeDataset = (o) => {
    subscriptions++;
    error = o.onError;
    return () => {};
  };
  const { client, clock } = setup(a);
  await client.start();
  await client.subscribeDataset("fixture-d");
  error({ code: "UNAVAILABLE" });
  clock.advance(1000);
  await client.tick();
  assert.equal(subscriptions, 2);
  assert.equal(
    client.state.datasets.get("fixture-d-stream").needsSnapshot,
    false,
  );
  client.stop();
});

test("dataset snapshot expiry clears session and stops retries", async () => {
  const a = transport();
  a.getSnapshot = async () => F.controlWithDataset();
  a.getDatasetSnapshot = async () => {
    throw { code: "SESSION_EXPIRED" };
  };
  a.subscribeDataset = () => () => {};
  const { client } = setup(a);
  await client.start();
  await client.subscribeDataset("fixture-d");
  assert.equal(client.state.status, "AUTH_REQUIRED");
  assert.equal(client.state.resources.size, 0);
  client.stop();
});
test("late dataset snapshot rejection cannot expire a newer connection", async () => {
  const a = transport();
  let reject;
  a.getSnapshot = async () => F.controlWithDataset();
  a.getDatasetSnapshot = () => new Promise((_, r) => (reject = r));
  a.subscribeDataset = () => () => {};
  const { client, clock } = setup(a);
  await client.start();
  const pending = client.subscribeDataset("fixture-d");
  a.error({ code: "UNAVAILABLE" });
  clock.advance(1000);
  await client.tick();
  reject({ code: "SESSION_EXPIRED" });
  await pending;
  assert.equal(client.state.status, "LIVE");
  client.stop();
});
test("buffer accepts more than half of its advertised byte capacity", async () => {
  const a = transport(),
    { client } = setup(a);
  await client.start();
  const e = F.event();
  e.payload.upserts[0].value.note = "a".repeat(50000);
  for (let i = 0; i < 11; i++) a.event(e);
  assert.equal(client.state.status, "LIVE");
  assert.equal(client.queue.length, 11);
  client.stop();
  await client.flush();
});

test("synchronous control subscribe failure cannot resurrect LIVE and closes its handle", async () => {
  const a = transport();
  let subscriptions = 0,
    closed = 0;
  a.subscribe = (o) => {
    subscriptions++;
    o.onError({ code: "UNAVAILABLE" });
    return () => closed++;
  };
  const { client, clock } = setup(a);
  await client.start();
  assert.notEqual(client.state.status, "LIVE");
  assert.equal(client.state.connected, false);
  assert.equal(closed, 1);
  clock.advance(1001);
  await client.tick();
  assert.equal(subscriptions, 2);
  assert.equal(closed, 2);
  client.stop();
});
test("synchronous dataset subscribe failure closes late handle and reports resync", async () => {
  const a = transport();
  let closed = 0;
  a.getSnapshot = async () => F.controlWithDataset();
  a.getDatasetSnapshot = async () => F.datasetSnapshot();
  a.subscribeDataset = (o) => {
    o.onError({ code: "UNAVAILABLE" });
    return () => closed++;
  };
  const { client } = setup(a);
  await client.start();
  const result = await client.subscribeDataset("fixture-d");
  assert.equal(result, "RESYNC_REQUIRED");
  assert.equal(closed, 1);
  assert.equal(client.datasetTasks.size, 0);
  client.stop();
});

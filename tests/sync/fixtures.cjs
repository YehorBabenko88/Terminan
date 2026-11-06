// SYNTHETIC ONLY: deterministic transport fixtures; never imported by production UI.
const time = Date.parse("2026-11-06T12:00:00Z");
const iso = (n) => new Date(time + n).toISOString();
const authority = () => ({
  state: "QUORUM_CONFIRMED",
  observed_at_utc: iso(0),
  fresh_until_utc: iso(15000),
  evidence_refs: ["fixture-e1"],
});
const descriptor = () => ({
  stream_id: "fixture-control",
  sequence_scope: "GLOBAL_CONTROL",
  dataset_id: null,
  event_sequence: 10,
  cluster_generation: "fixture-g1",
  schema_version: "1.0",
  cursor: "fixture-c10",
  retention_window: { minimum_seconds: 600, earliest_available_sequence: 0 },
  payload_size_limit: 65536,
});
const resource = () => ({
  resource_id: "fixture-job",
  resource_type: "job",
  resource_revision: 1,
  metadata_revision: 5,
  cluster_generation: "fixture-g1",
  evidence_refs: ["fixture-e1"],
  value: { state: "RUNNING", progress: 10 },
});
const snapshot = () => ({
  schema_version: "1.0",
  snapshot_scope: "CONTROL",
  dataset_id: null,
  dataset_revision: null,
  cluster_id: "fixture-cluster",
  cluster_generation: "fixture-g1",
  revision: 5,
  cursor: "fixture-c10",
  authority_status: authority(),
  generated_at_utc: iso(0),
  fresh_until_utc: iso(15000),
  evidence_refs: ["fixture-e1"],
  control_stream: descriptor(),
  dataset_streams: [],
  resources: [resource()],
});
const event = () => ({
  schema_version: "1.0",
  cluster_id: "fixture-cluster",
  cluster_generation: "fixture-g1",
  stream_id: "fixture-control",
  sequence_scope: "GLOBAL_CONTROL",
  dataset_id: null,
  event_id: "fixture-event11",
  event_sequence: 11,
  cursor: "fixture-c11",
  retention_window: { minimum_seconds: 600, earliest_available_sequence: 0 },
  payload_size_limit: 65536,
  metadata_revision: 6,
  previous_revision: 5,
  revision: 6,
  type: "CONTROL_CHANGED",
  observed_at_utc: iso(1000),
  fresh_until_utc: iso(15000),
  evidence_refs: ["fixture-e1"],
  authority_status: authority(),
  payload: {
    upserts: [
      {
        ...resource(),
        resource_revision: 2,
        metadata_revision: 6,
        value: { state: "RUNNING", progress: 20 },
      },
    ],
    deletes: [],
  },
});
const clock = () => ({
  wall: time,
  mono: 0,
  now() {
    return { wall: this.wall, mono: this.mono };
  },
  advance(n) {
    this.wall += n;
    this.mono += n;
  },
});
module.exports = {
  time,
  iso,
  authority,
  descriptor,
  resource,
  snapshot,
  event,
  clock,
};

const datasetDescriptor = () => ({
  ...descriptor(),
  stream_id: "fixture-d-stream",
  sequence_scope: "DATASET",
  dataset_id: "fixture-d",
  event_sequence: 20,
  cursor: "fixture-d20",
});
const controlWithDataset = () => ({
  ...snapshot(),
  dataset_streams: [datasetDescriptor()],
});
const datasetSnapshot = () => ({
  ...snapshot(),
  snapshot_scope: "DATASET",
  dataset_id: "fixture-d",
  dataset_revision: 2,
  dataset_streams: [datasetDescriptor()],
});
const datasetHeartbeat = () => ({
  ...event(),
  stream_id: "fixture-d-stream",
  sequence_scope: "DATASET",
  dataset_id: "fixture-d",
  event_id: "fixture-d21",
  event_sequence: 21,
  cursor: "fixture-d21",
  metadata_revision: 5,
  previous_revision: 2,
  revision: 2,
  type: "HEARTBEAT",
  payload: { upserts: [], deletes: [] },
});
Object.assign(module.exports, {
  datasetDescriptor,
  controlWithDataset,
  datasetSnapshot,
  datasetHeartbeat,
});

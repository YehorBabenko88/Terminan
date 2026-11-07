/* Sync v1 consumer. No authority, credentials, mutations or endpoint assumptions. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object") module.exports = api;
  else root.TerminanSync = api;
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";
  const MAX = Number.MAX_SAFE_INTEGER,
    ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
  const fail = () => {
    throw new Error("INVALID_CONTRACT");
  };
  const integer = (x) => Number.isSafeInteger(x) && x >= 0;
  const id = (x) => typeof x === "string" && ID.test(x);
  const plain = (x) =>
    x !== null &&
    typeof x === "object" &&
    !Array.isArray(x) &&
    Object.getPrototypeOf(x) === Object.prototype;
  function keys(x, list) {
    if (
      !plain(x) ||
      Object.keys(x).length !== list.length ||
      list.some((k) => !Object.hasOwn(x, k))
    )
      fail();
  }
  function timestamp(x) {
    if (
      typeof x !== "string" ||
      !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,3})?Z$/.test(x) ||
      !Number.isFinite(Date.parse(x))
    )
      fail();
    return Date.parse(x);
  }
  function evidence(x) {
    if (!Array.isArray(x) || x.length > 64 || x.some((v) => !id(v))) fail();
  }
  function bounded(x, depth = 0) {
    if (depth > 16) fail();
    if (typeof x === "number" && !Number.isFinite(x)) fail();
    if (Array.isArray(x)) {
      if (x.length > 1000) fail();
      x.forEach((v) => bounded(v, depth + 1));
    } else if (x && typeof x === "object") {
      if (!plain(x) || Object.keys(x).length > 64) fail();
      for (const [k, v] of Object.entries(x)) {
        if (["__proto__", "prototype", "constructor"].includes(k)) fail();
        bounded(v, depth + 1);
      }
    }
  }
  function parseBounded(text, kind) {
    const limit = kind === "snapshot" ? 2097152 : 65536;
    if (
      typeof text !== "string" ||
      new TextEncoder().encode(text).length > limit
    )
      fail();
    // Structural scanner rejects duplicate keys before JSON.parse loses that evidence.
    let i = 0;
    const ws = () => {
      while (/\s/.test(text[i] || "") && i < text.length) i++;
    };
    function str() {
      const start = i++;
      while (i < text.length) {
        if (text[i] === "\\") {
          i += 2;
          continue;
        }
        if (text[i++] === '"') return JSON.parse(text.slice(start, i));
      }
      fail();
    }
    function value(d) {
      if (d > 16) fail();
      ws();
      if (text[i] === "{") {
        i++;
        ws();
        const seen = new Set();
        if (text[i] === "}") {
          i++;
          return;
        }
        for (;;) {
          ws();
          if (text[i] !== '"') fail();
          const k = str();
          if (seen.has(k)) fail();
          seen.add(k);
          ws();
          if (text[i++] !== ":") fail();
          value(d + 1);
          ws();
          const c = text[i++];
          if (c === "}") return;
          if (c !== ",") fail();
        }
      } else if (text[i] === "[") {
        i++;
        ws();
        if (text[i] === "]") {
          i++;
          return;
        }
        for (;;) {
          value(d + 1);
          ws();
          const c = text[i++];
          if (c === "]") return;
          if (c !== ",") fail();
        }
      } else if (text[i] === '"') str();
      else {
        const m =
          /^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(
            text.slice(i),
          );
        if (!m) fail();
        i += m[0].length;
      }
    }
    value(0);
    ws();
    if (i !== text.length) fail();
    const x = JSON.parse(text);
    bounded(x);
    return x;
  }
  function clone(x, kind) {
    return parseBounded(JSON.stringify(x), kind);
  }
  function authority(x) {
    keys(x, ["state", "observed_at_utc", "fresh_until_utc", "evidence_refs"]);
    if (!["QUORUM_CONFIRMED", "NO_QUORUM", "UNKNOWN"].includes(x.state)) fail();
    if (
      timestamp(x.fresh_until_utc) <= timestamp(x.observed_at_utc) ||
      timestamp(x.fresh_until_utc) - timestamp(x.observed_at_utc) > 15000
    )
      fail();
    evidence(x.evidence_refs);
    if (x.state === "QUORUM_CONFIRMED" && !x.evidence_refs.length) fail();
  }
  function retention(x) {
    keys(x, ["minimum_seconds", "earliest_available_sequence"]);
    if (
      !integer(x.minimum_seconds) ||
      x.minimum_seconds < 600 ||
      x.minimum_seconds > 604800 ||
      !integer(x.earliest_available_sequence)
    )
      fail();
  }
  function cursor(x) {
    if (typeof x !== "string" || !x.length || x.length > 2048) fail();
  }
  function stream(x) {
    keys(x, [
      "stream_id",
      "sequence_scope",
      "dataset_id",
      "event_sequence",
      "cluster_generation",
      "schema_version",
      "cursor",
      "retention_window",
      "payload_size_limit",
    ]);
    if (
      !id(x.stream_id) ||
      !id(x.cluster_generation) ||
      x.schema_version !== "1.0" ||
      !integer(x.event_sequence) ||
      !integer(x.payload_size_limit) ||
      x.payload_size_limit < 1 ||
      x.payload_size_limit > 65536
    )
      fail();
    if (x.sequence_scope === "GLOBAL_CONTROL") {
      if (x.dataset_id !== null) fail();
    } else if (x.sequence_scope !== "DATASET" || !id(x.dataset_id)) fail();
    cursor(x.cursor);
    retention(x.retention_window);
    if (x.retention_window.earliest_available_sequence > x.event_sequence)
      fail();
  }
  function resource(x, g, revision, validator) {
    keys(x, [
      "resource_id",
      "resource_type",
      "resource_revision",
      "metadata_revision",
      "cluster_generation",
      "evidence_refs",
      "value",
    ]);
    if (
      !id(x.resource_id) ||
      !id(x.resource_type) ||
      !integer(x.resource_revision) ||
      !integer(x.metadata_revision) ||
      x.metadata_revision > revision ||
      x.cluster_generation !== g ||
      !plain(x.value)
    )
      fail();
    evidence(x.evidence_refs);
    if (typeof validator !== "function" || validator(x) !== true) fail();
  }
  function deadline(observed, fresh, auth, now) {
    const t = timestamp(observed),
      end = timestamp(fresh);
    if (
      end <= t ||
      end - t > 15000 ||
      t > now.wall + 2000 ||
      timestamp(auth.observed_at_utc) > now.wall + 2000
    )
      fail();
    return (
      now.mono +
      Math.max(
        0,
        Math.min(
          15000,
          end - now.wall,
          timestamp(auth.fresh_until_utc) - now.wall,
        ),
      )
    );
  }
  const snapshotKeys = [
    "schema_version",
    "snapshot_scope",
    "dataset_id",
    "dataset_revision",
    "cluster_id",
    "cluster_generation",
    "revision",
    "cursor",
    "authority_status",
    "generated_at_utc",
    "fresh_until_utc",
    "evidence_refs",
    "control_stream",
    "dataset_streams",
    "resources",
  ];
  const eventKeys = [
    "schema_version",
    "cluster_id",
    "cluster_generation",
    "stream_id",
    "sequence_scope",
    "dataset_id",
    "event_id",
    "event_sequence",
    "cursor",
    "retention_window",
    "payload_size_limit",
    "metadata_revision",
    "previous_revision",
    "revision",
    "type",
    "observed_at_utc",
    "fresh_until_utc",
    "evidence_refs",
    "authority_status",
    "payload",
  ];
  class SyncState {
    constructor({ clock, validateDomain } = {}) {
      this.clock =
        clock || (() => ({ wall: Date.now(), mono: performance.now() }));
      this.validateDomain = validateDomain;
      this.status = "UNAVAILABLE";
      this.transport = "DISCONNECTED";
      this.resources = new Map();
      this.datasets = new Map();
      this.revision = null;
      this.cursor = null;
      this.resumeCursor = null;
      this.generation = null;
      this.cluster = null;
      this.sequence = null;
      this.deadline = 0;
      this.connected = false;
      this.authenticated = false;
      this.needsSnapshot = true;
      this.seen = new Map();
      this.descriptors = new Map();
      this.tombstones = new Set();
      this.lastContact = null;
      this.stopped = false;
    }
    install(input) {
      try {
        const x = clone(input, "snapshot");
        keys(x, snapshotKeys);
        if (
          x.schema_version !== "1.0" ||
          !id(x.cluster_id) ||
          !id(x.cluster_generation) ||
          !integer(x.revision)
        )
          fail();
        cursor(x.cursor);
        authority(x.authority_status);
        evidence(x.evidence_refs);
        stream(x.control_stream);
        if (
          x.control_stream.sequence_scope !== "GLOBAL_CONTROL" ||
          x.control_stream.cluster_generation !== x.cluster_generation ||
          x.control_stream.cursor !== x.cursor
        )
          fail();
        if (
          !Array.isArray(x.dataset_streams) ||
          x.dataset_streams.length > 128 ||
          !Array.isArray(x.resources) ||
          x.resources.length > 1000
        )
          fail();
        const descriptors = new Map([
          [x.control_stream.stream_id, x.control_stream],
        ]);
        for (const d of x.dataset_streams) {
          stream(d);
          if (
            d.sequence_scope !== "DATASET" ||
            d.cluster_generation !== x.cluster_generation ||
            descriptors.has(d.stream_id)
          )
            fail();
          descriptors.set(d.stream_id, d);
        }
        const records = new Map();
        for (const r of x.resources) {
          resource(r, x.cluster_generation, x.revision, this.validateDomain);
          if (records.has(r.resource_id)) fail();
          records.set(r.resource_id, r);
        }
        const now = this.clock(),
          until = deadline(
            x.generated_at_utc,
            x.fresh_until_utc,
            x.authority_status,
            now,
          );
        if (x.snapshot_scope === "DATASET") {
          if (
            !id(x.dataset_id) ||
            !integer(x.dataset_revision) ||
            x.dataset_streams.length !== 1 ||
            x.dataset_streams[0].dataset_id !== x.dataset_id ||
            this.needsSnapshot ||
            x.cluster_id !== this.cluster ||
            x.cluster_generation !== this.generation ||
            x.revision !== this.revision
          )
            fail();
          const d = x.dataset_streams[0];
          this.datasets.set(d.stream_id, {
            revision: x.dataset_revision,
            sequence: d.event_sequence,
            cursor: d.cursor,
            resources: records,
            seen: new Map(),
            tombstones: new Set(),
            deadline: until,
            needsSnapshot: false,
          });
          if (x.authority_status.state !== "QUORUM_CONFIRMED") {
            this.authority = x.authority_status.state;
            this.deadline = Math.min(this.deadline, until);
            this.tick();
          }
          return;
        }
        if (
          x.snapshot_scope !== "CONTROL" ||
          x.dataset_id !== null ||
          x.dataset_revision !== null
        )
          fail();
        if (this.cluster && x.cluster_id !== this.cluster) fail();
        if (
          x.cluster_generation === this.generation &&
          this.revision !== null &&
          x.revision < this.revision
        )
          fail();
        this.resources = records;
        this.revision = x.revision;
        this.cursor = x.cursor;
        this.resumeCursor = x.cursor;
        this.generation = x.cluster_generation;
        this.cluster = x.cluster_id;
        this.sequence = x.control_stream.event_sequence;
        this.controlStream = x.control_stream.stream_id;
        this.descriptors = descriptors;
        this.authority = x.authority_status.state;
        this.deadline = until;
        this.seen.clear();
        this.tombstones.clear();
        this.datasets.clear();
        this.authenticated = true;
        this.stopped = false;
        this.needsSnapshot = false;
        this.lastContact = now.mono;
        this.tick();
      } catch (e) {
        this.status = "STALE";
        this.needsSnapshot = true;
        this.resumeCursor = null;
        throw new Error("INVALID_SNAPSHOT");
      }
    }
    resync() {
      this.needsSnapshot = true;
      this.resumeCursor = null;
      this.status = "RESYNCING";
      return "RESYNC_REQUIRED";
    }
    apply(input) {
      if (this.stopped || !this.authenticated || this.needsSnapshot)
        return "IGNORED";
      try {
        const x = clone(input, "event");
        keys(x, eventKeys);
        if (
          x.schema_version !== "1.0" ||
          x.cluster_id !== this.cluster ||
          !id(x.cluster_generation) ||
          !id(x.event_id)
        )
          fail();
        if (x.cluster_generation !== this.generation) return this.resync();
        authority(x.authority_status);
        evidence(x.evidence_refs);
        retention(x.retention_window);
        cursor(x.cursor);
        if (
          !integer(x.event_sequence) ||
          !integer(x.metadata_revision) ||
          !integer(x.previous_revision) ||
          !integer(x.revision) ||
          !integer(x.payload_size_limit) ||
          x.payload_size_limit < 1 ||
          x.payload_size_limit > 65536
        )
          fail();
        const d = this.descriptors.get(x.stream_id);
        if (
          !d ||
          d.sequence_scope !== x.sequence_scope ||
          d.dataset_id !== x.dataset_id
        )
          fail();
        if (
          new TextEncoder().encode(JSON.stringify(x)).length >
          Math.min(d.payload_size_limit, x.payload_size_limit)
        )
          fail();
        keys(x.payload, ["upserts", "deletes"]);
        if (
          !Array.isArray(x.payload.upserts) ||
          !Array.isArray(x.payload.deletes) ||
          x.payload.upserts.length + x.payload.deletes.length > 100 ||
          x.payload.deletes.some((v) => !id(v))
        )
          fail();
        const isControl = x.sequence_scope === "GLOBAL_CONTROL";
        const target = isControl ? this : this.datasets.get(x.stream_id);
        if (!target || target.needsSnapshot) return "RESYNC_REQUIRED";
        if (!isControl && x.metadata_revision !== this.revision) {
          target.needsSnapshot = true;
          return "RESYNC_REQUIRED";
        }
        const serialized = JSON.stringify(x);
        const prior = target.seen.get(x.event_sequence);
        if (x.event_sequence <= target.sequence) {
          if (prior === serialized) return "DUPLICATE";
          if (isControl) return this.resync();
          target.needsSnapshot = true;
          return "RESYNC_REQUIRED";
        }
        if (
          x.event_sequence !== target.sequence + 1 ||
          [...target.seen.values()].some(
            (v) => JSON.parse(v).event_id === x.event_id,
          )
        )
          fail();
        if (x.previous_revision !== target.revision) fail();
        const heartbeat = x.type === "HEARTBEAT";
        if (heartbeat) {
          if (
            x.revision !== target.revision ||
            x.payload.upserts.length ||
            x.payload.deletes.length
          )
            fail();
        } else if (
          x.type !== (isControl ? "CONTROL_CHANGED" : "DATASET_CHANGED") ||
          x.revision !== target.revision + 1
        )
          fail();
        if (isControl && x.metadata_revision !== x.revision) fail();
        const changed = new Set(x.payload.deletes);
        if (changed.size !== x.payload.deletes.length) fail();
        const records = new Map(target.resources),
          tombstones = new Set(target.tombstones);
        for (const r of x.payload.upserts) {
          resource(
            r,
            this.generation,
            isControl ? x.revision : this.revision,
            this.validateDomain,
          );
          if (changed.has(r.resource_id) || tombstones.has(r.resource_id))
            fail();
          changed.add(r.resource_id);
          const old = records.get(r.resource_id);
          if (
            old &&
            (old.resource_type !== r.resource_type ||
              r.resource_revision <= old.resource_revision)
          )
            fail();
          records.set(r.resource_id, r);
        }
        for (const rid of x.payload.deletes) {
          if (!records.has(rid)) fail();
          records.delete(rid);
          tombstones.add(rid);
        }
        if (records.size > 1000 || tombstones.size > 1000) fail();
        const now = this.clock(),
          until = deadline(
            x.observed_at_utc,
            x.fresh_until_utc,
            x.authority_status,
            now,
          );
        target.resources = records;
        target.tombstones = tombstones;
        target.revision = x.revision;
        target.sequence = x.event_sequence;
        target.cursor = x.cursor;
        target.deadline = until;
        target.seen.set(x.event_sequence, serialized);
        while (target.seen.size > 256)
          target.seen.delete(target.seen.keys().next().value);
        if (isControl) {
          this.resumeCursor = x.cursor;
          this.authority = x.authority_status.state;
          this.lastContact = now.mono;
          this.tick();
        } else if (x.authority_status.state !== "QUORUM_CONFIRMED") {
          this.authority = x.authority_status.state;
          this.tick();
        }
        return "APPLIED";
      } catch (e) {
        return this.resync();
      }
    }
    connection(connected) {
      if (this.stopped || !this.authenticated || this.needsSnapshot) return;
      this.connected = connected;
      this.transport = connected ? "CONNECTED" : "RECONNECTING";
      if (connected) this.lastContact = this.clock().mono;
      this.tick();
    }
    tick() {
      if (this.stopped || !this.authenticated || this.needsSnapshot) return;
      const n = this.clock();
      if (!this.connected && n.mono - this.lastContact >= 30000) {
        this.status = "OFFLINE";
        return;
      }
      if (n.mono >= this.deadline || this.authority === "UNKNOWN") {
        this.status = "STALE";
        return;
      }
      this.status =
        this.authority === "NO_QUORUM"
          ? "NO_QUORUM"
          : this.connected
            ? "LIVE"
            : "RECONNECTING";
    }
    error(error) {
      const code = error && error.code;
      if (["UNAUTHENTICATED", "SESSION_EXPIRED", "FORBIDDEN"].includes(code)) {
        this.resources.clear();
        this.datasets.clear();
        this.seen.clear();
        this.cursor = null;
        this.resumeCursor = null;
        this.authenticated = false;
        this.connected = false;
        this.needsSnapshot = true;
        this.status = code === "FORBIDDEN" ? "FORBIDDEN" : "AUTH_REQUIRED";
        return;
      }
      if (code === "RESYNC_REQUIRED") {
        this.resync();
        return;
      }
      this.connection(false);
    }
    stop() {
      this.stopped = true;
      this.connected = false;
      this.status = "OFFLINE";
      this.transport = "DISCONNECTED";
    }
    command() {
      throw new Error("COMMAND_UNAVAILABLE");
    }
    get canMutate() {
      return false;
    }
  }
  function integrityDimensions(value = {}) {
    return [
      "byte_integrity",
      "source_completeness",
      "redundancy",
      "authority_freshness",
    ].map((key) => ({
      key,
      ...(plain(value[key]) ? value[key] : { state: "UNKNOWN" }),
    }));
  }
  return { SyncState, parseBounded, integrityDimensions };
});

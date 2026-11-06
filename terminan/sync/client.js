/* Injected read-only transport orchestration. No default URLs or backend commands. */
(function (root, factory) {
  const api = factory(
    typeof module === "object" ? require("./protocol.js") : root.TerminanSync,
  );
  if (typeof module === "object") module.exports = api;
  else root.TerminanSyncClient = api;
})(globalThis, function (P) {
  "use strict";
  class SyncClient {
    constructor({ adapter, clock, random, onChange, validateDomain } = {}) {
      this.adapter = adapter;
      this.clock =
        clock || (() => ({ wall: Date.now(), mono: performance.now() }));
      this.random = random || Math.random;
      this.onChange = onChange || (() => {});
      this.state = new P.SyncState({ clock: this.clock, validateDomain });
      this.attempts = [];
      this.failureCount = 0;
      this.nextAttempt = 0;
      this.epoch = 0;
      this.active = false;
      this.busy = false;
      this.queue = [];
      this.bytes = 0;
      this.flushing = null;
      this.datasetTasks = new Map();
      this.desiredDatasets = new Set();
      this.datasetRetry = new Map();
      this.pending = [];
      this.controller = null;
      this.closeStream = null;
    }
    notify() {
      this.onChange(this.state);
    }
    async start() {
      this.active = true;
      await this.connect();
    }
    disconnect() {
      if (this.controller) this.controller.abort();
      this.controller = null;
      if (this.closeStream) {
        try {
          this.closeStream();
        } catch {}
        this.closeStream = null;
      }
      this.queue = [];
      this.bytes = 0;
      for (const task of this.datasetTasks.values()) {
        task.controller.abort();
        if (task.close)
          try {
            task.close();
          } catch {}
      }
      this.datasetTasks.clear();
      this.pending = [];
    }
    schedule(error = {}) {
      this.failureCount++;
      const ceiling = Math.min(
        30000,
        1000 * 2 ** Math.min(this.failureCount - 1, 5),
      );
      const delay = Math.max(
        1000,
        Math.floor(this.random() * ceiling),
        Math.min(300000, Math.max(0, Number(error.retry_after_ms) || 0)),
      );
      this.nextAttempt = this.clock().mono + delay;
    }
    async connect() {
      if (!this.active || this.busy) return;
      if (
        !this.adapter ||
        typeof this.adapter.getSnapshot !== "function" ||
        typeof this.adapter.subscribe !== "function"
      ) {
        this.state.status = "UNAVAILABLE";
        this.notify();
        return;
      }
      const now = this.clock().mono;
      this.attempts = this.attempts.filter((t) => now - t < 60000);
      if (now < this.nextAttempt || this.attempts.length >= 6) return;
      this.attempts.push(now);
      this.busy = true;
      this.disconnect();
      const epoch = ++this.epoch;
      this.controller = new AbortController();
      const signal = this.controller.signal;
      try {
        if (this.state.needsSnapshot || !this.state.authenticated) {
          const data = await this.adapter.getSnapshot({ signal });
          if (!this.active || epoch !== this.epoch) return;
          this.state.install(
            typeof data === "string" ? P.parseBounded(data, "snapshot") : data,
          );
        }
        if (!this.active || epoch !== this.epoch) return;
        const close = this.adapter.subscribe({
          cursor: this.state.resumeCursor,
          signal,
          onEvent: (x) => this.enqueue(x, epoch),
          onError: (e) => this.handleError(e, epoch),
        });
        if (!this.active || epoch !== this.epoch || signal.aborted) {
          if (typeof close === "function") close();
          return;
        }
        this.closeStream = close;
        this.state.connection(true);
        this.nextAttempt = now + 1000;
        for (const id of this.desiredDatasets)
          this.datasetRetry.set(id, now + 1000);
        this.notify();
      } catch (error) {
        if (this.active && epoch === this.epoch) this.handleError(error, epoch);
      } finally {
        if (epoch === this.epoch) this.busy = false;
      }
    }
    handleError(error, epoch = this.epoch) {
      if (!this.active || epoch !== this.epoch) return;
      this.state.error(error);
      this.disconnect();
      if (!["AUTH_REQUIRED", "FORBIDDEN"].includes(this.state.status))
        this.schedule(error);
      this.notify();
    }
    enqueue(value, epoch = this.epoch) {
      if (!this.active || epoch !== this.epoch || this.state.needsSnapshot)
        return;
      try {
        const size = new TextEncoder().encode(
          typeof value === "string" ? value : JSON.stringify(value),
        ).length;
        if (
          size > 65536 ||
          this.queue.length >= 256 ||
          this.bytes + this.pending.reduce((n, x) => n + x.size, 0) + size >
            1048576
        )
          throw new Error();
        this.queue.push(value);
        this.bytes += size;
        if (!this.flushing)
          this.flushing = Promise.resolve()
            .then(() => this.drain(epoch))
            .finally(() => {
              this.flushing = null;
            });
      } catch {
        this.handleError(
          { code: "RESYNC_REQUIRED", reason: "BUFFER_OVERFLOW" },
          epoch,
        );
      }
    }
    drain(epoch) {
      while (
        this.queue.length &&
        this.active &&
        epoch === this.epoch &&
        !this.state.needsSnapshot
      ) {
        const raw = this.queue.shift();
        this.bytes -= new TextEncoder().encode(
          typeof raw === "string" ? raw : JSON.stringify(raw),
        ).length;
        let event;
        try {
          event = typeof raw === "string" ? P.parseBounded(raw, "event") : raw;
        } catch {
          this.handleError({ code: "RESYNC_REQUIRED" }, epoch);
          break;
        }
        if (
          event.sequence_scope === "DATASET" &&
          event.metadata_revision > this.state.revision
        ) {
          const size = new TextEncoder().encode(JSON.stringify(event)).length;
          if (
            this.pending.length >= 256 ||
            this.bytes + this.pending.reduce((n, x) => n + x.size, 0) + size >
              1048576
          ) {
            this.handleError({ code: "RESYNC_REQUIRED" }, epoch);
            break;
          }
          this.pending.push({ event, size, until: this.clock().mono + 10000 });
          continue;
        }
        const result = this.state.apply(event);
        if (result === "RESYNC_REQUIRED") {
          if (event.sequence_scope === "DATASET" && !this.state.needsSnapshot) {
            void this.subscribeDataset(event.dataset_id, true);
          } else this.handleError({ code: "RESYNC_REQUIRED" }, epoch);
          break;
        }
        if (result === "APPLIED") {
          this.failureCount = 0;
          this.notify();
          this.drainPending();
        }
      }
    }
    drainPending() {
      const waiting = this.pending;
      this.pending = [];
      for (const p of waiting) {
        if (
          p.until <= this.clock().mono ||
          p.event.metadata_revision < this.state.revision
        ) {
          void this.subscribeDataset(p.event.dataset_id, true);
        } else if (p.event.metadata_revision === this.state.revision) {
          if (this.state.apply(p.event) === "RESYNC_REQUIRED")
            void this.subscribeDataset(p.event.dataset_id, true);
        } else this.pending.push(p);
      }
    }
    async subscribeDataset(datasetId, replace = false) {
      if (
        !this.active ||
        !this.state.authenticated ||
        !this.state.connected ||
        this.state.needsSnapshot ||
        !this.adapter ||
        typeof this.adapter.getDatasetSnapshot !== "function" ||
        typeof this.adapter.subscribeDataset !== "function"
      )
        return "UNAVAILABLE";
      if (
        ![...this.state.descriptors.values()].some(
          (d) => d.dataset_id === datasetId,
        )
      )
        return "UNAVAILABLE";
      this.desiredDatasets.add(datasetId);
      const existing = this.datasetTasks.get(datasetId);
      if (existing) {
        if (!replace) return "SUBSCRIBED";
        existing.controller.abort();
        if (existing.close) existing.close();
        this.datasetTasks.delete(datasetId);
      }
      if (this.datasetTasks.size >= 4) return "LIMIT";
      const now = this.clock().mono;
      this.attempts = this.attempts.filter((t) => now - t < 60000);
      if (this.attempts.length >= 6) {
        this.datasetRetry.set(datasetId, now + 1000);
        return "LIMIT";
      }
      this.attempts.push(now);
      this.datasetRetry.delete(datasetId);
      const epoch = this.epoch,
        barrier = this.state.revision,
        task = { controller: new AbortController() };
      this.datasetTasks.set(datasetId, task);
      try {
        const data = await this.adapter.getDatasetSnapshot({
          datasetId,
          metadataRevision: barrier,
          signal: task.controller.signal,
        });
        if (
          !this.active ||
          epoch !== this.epoch ||
          task.controller.signal.aborted
        )
          return "IGNORED";
        this.state.install(
          typeof data === "string" ? P.parseBounded(data, "snapshot") : data,
        );
        if (this.state.revision !== barrier) return "RESYNC_REQUIRED";
        const dataset = [...this.state.descriptors.values()].find(
          (d) => d.dataset_id === datasetId,
        );
        if (!dataset) throw new Error();
        const position = this.state.datasets.get(dataset.stream_id);
        const close = this.adapter.subscribeDataset({
          datasetId,
          cursor: position.cursor,
          signal: task.controller.signal,
          onEvent: (e) => {
            if (!task.controller.signal.aborted) this.enqueue(e, epoch);
          },
          onError: (error) => {
            if (task.controller.signal.aborted || epoch !== this.epoch) return;
            if (
              ["UNAUTHENTICATED", "SESSION_EXPIRED", "FORBIDDEN"].includes(
                error && error.code,
              )
            ) {
              this.handleError(error, epoch);
              return;
            }
            position.needsSnapshot = true;
            task.controller.abort();
            if (task.close) task.close();
            this.datasetTasks.delete(datasetId);
            this.datasetRetry.set(
              datasetId,
              this.clock().mono +
                Math.max(
                  1000,
                  Math.min(
                    300000,
                    Number(error && error.retry_after_ms) || 1000,
                  ),
                ),
            );
            this.notify();
          },
        });
        if (
          !this.active ||
          epoch !== this.epoch ||
          task.controller.signal.aborted ||
          this.datasetTasks.get(datasetId) !== task
        ) {
          if (typeof close === "function") close();
          return "RESYNC_REQUIRED";
        }
        task.close = close;
        this.notify();
        return "SUBSCRIBED";
      } catch (error) {
        if (
          !this.active ||
          epoch !== this.epoch ||
          task.controller.signal.aborted ||
          this.datasetTasks.get(datasetId) !== task
        )
          return "IGNORED";
        if (
          ["UNAUTHENTICATED", "SESSION_EXPIRED", "FORBIDDEN"].includes(
            error && error.code,
          )
        ) {
          this.handleError(error, epoch);
          return "AUTH_REQUIRED";
        }
        this.datasetTasks.delete(datasetId);
        this.datasetRetry.set(datasetId, this.clock().mono + 1000);
        this.notify();
        return "RESYNC_REQUIRED";
      }
    }
    async flush() {
      if (this.flushing) await this.flushing;
    }
    async tick() {
      if (!this.active) return;
      this.state.tick();
      this.drainPending();
      this.notify();
      if (
        !["AUTH_REQUIRED", "FORBIDDEN", "UNAVAILABLE"].includes(
          this.state.status,
        ) &&
        (!this.state.connected || this.state.needsSnapshot)
      )
        await this.connect();
      if (this.state.connected && !this.state.needsSnapshot)
        for (const [id, time] of [...this.datasetRetry])
          if (time <= this.clock().mono) await this.subscribeDataset(id, true);
    }
    stop() {
      this.active = false;
      this.epoch++;
      this.busy = false;
      this.disconnect();
      this.desiredDatasets.clear();
      this.datasetRetry.clear();
      this.state.stop();
      this.notify();
    }
  }
  return { SyncClient };
});

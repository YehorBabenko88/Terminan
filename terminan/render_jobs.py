"""Serialized render-job state transitions with an irreversible close tombstone.

A dequeued job must call begin() immediately before its action. Cancellation
before begin prevents execution; cancellation after begin cannot interrupt
an already-running action. No threads or external scheduler are assumed.
"""
from dataclasses import dataclass
from enum import Enum, auto
from threading import RLock


class JobState(Enum):
    PENDING = auto()
    RUNNING = auto()
    FINISHED = auto()
    CANCELLED = auto()


@dataclass
class RenderJob:
    generation: int
    action: object
    cleanup: object = None
    state: JobState = JobState.PENDING
    cleaned: bool = False

    def begin(self):
        if self.state is not JobState.PENDING:
            return False
        self.state = JobState.RUNNING
        return True

    def finish(self):
        if self.state is not JobState.RUNNING:
            return False
        self.state = JobState.FINISHED
        self.release()
        return True

    def cancel(self):
        if self.state in (JobState.PENDING, JobState.RUNNING):
            # A running action cannot be preempted; its completion must
            # still release resources and must pass the presentation gate.
            if self.state is JobState.PENDING:
                self.state = JobState.CANCELLED
                self.release()
            return True
        return False

    def release(self):
        if not self.cleaned:
            self.cleaned = True
            if self.cleanup is not None:
                self.cleanup()


class RenderJobGate:
    """One pending job. Closing is a permanent submission tombstone."""

    def __init__(self):
        self.generation = 0
        self.pending = None
        self.closed = False
        self.replacements = 0
        self._lock = RLock()

    def submit(self, action, cleanup=None):
        with self._lock:
            if self.closed:
                if cleanup is not None:
                    cleanup()
                return None
            job = RenderJob(self.generation, action, cleanup)
            if self.pending is not None:
                self.pending.cancel()
                self.replacements += 1
            self.pending = job
            return job

    def dequeue(self):
        with self._lock:
            job, self.pending = self.pending, None
            return job

    def execute(self, job):
        with self._lock:
            # Direct execute() transfers ownership just like dequeue().
            # Otherwise close() may clean an already finished job twice.
            if job is not None and self.pending is job:
                self.pending = None
            if (self.closed or job is None or
                    job.generation != self.generation or not job.begin()):
                if job is not None:
                    job.cancel()
                return False
        try:
            # Never hold the gate lock while executing arbitrary work:
            # close/invalidate must be able to invalidate in-flight jobs.
            job.action()
            with self._lock:
                return not self.closed and job.generation == self.generation
        finally:
            with self._lock:
                job.finish()

    def invalidate(self):
        with self._lock:
            if self.closed:
                return
            self.generation += 1
            pending, self.pending = self.pending, None
            if pending is not None:
                pending.state = JobState.CANCELLED
                pending.cleaned = True
        if pending is not None and pending.cleanup is not None:
            pending.cleanup()

    def close(self):
        with self._lock:
            if self.closed:
                return
            self.closed = True
            pending, self.pending = self.pending, None
            if pending is not None:
                pending.state = JobState.CANCELLED
                pending.cleaned = True
        if pending is not None and pending.cleanup is not None:
            pending.cleanup()

    def invalidate_pending(self):
        with self._lock:
            pending, self.pending = self.pending, None
            if pending is not None:
                pending.state = JobState.CANCELLED
                pending.cleaned = True
        if pending is not None and pending.cleanup is not None:
            pending.cleanup()

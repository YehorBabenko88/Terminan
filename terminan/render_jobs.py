"""Single-owner cancellable render jobs with an irreversible close tombstone.

A dequeued job must call begin() immediately before its action. Cancellation
before begin prevents execution; cancellation after begin cannot interrupt
an already-running action. No threads or external scheduler are assumed.
"""
from dataclasses import dataclass
from enum import Enum, auto


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

    def submit(self, action, cleanup=None):
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
        job, self.pending = self.pending, None
        return job

    def execute(self, job):
        if (self.closed or job is None or
                job.generation != self.generation or not job.begin()):
            if job is not None:
                job.cancel()
            return False
        try:
            job.action()
            return not self.closed and job.generation == self.generation
        finally:
            job.finish()

    def invalidate(self):
        if self.closed:
            return
        self.generation += 1
        if self.pending is not None:
            self.pending.cancel()
            self.pending = None

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.invalidate_pending()

    def invalidate_pending(self):
        if self.pending is not None:
            self.pending.cancel()
            self.pending = None

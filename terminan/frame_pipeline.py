"""Pure synchronous DOM frame pipeline; no UI, threads, or exchange I/O.

Callers serialize reset/offer/pump/dispose on the UI owner thread.
A real UI adapter must marshal callbacks to that thread.
"""
from dataclasses import dataclass
from .frame_scheduler import LatestFrameMailbox
from .canvas_backend import FrameSwapchain, rasterize
from .render_model import RenderModel
from .render_jobs import RenderJobGate


@dataclass(frozen=True)
class PumpResult:
    reason: str
    published: bool


class DomFramePipeline:
    """One pending model and one immutable published RGBA buffer."""

    def __init__(self, fps=60):
        self.mailbox = LatestFrameMailbox(fps)
        self.swapchain = FrameSwapchain()
        self.jobs = RenderJobGate()
        self.closed = False
        self.last_version = -1
        self.last_revision = None
        self.renders = 0
        self.failed_renders = 0

    def reset(self, epoch, surface_generation=0, *, retain_front=False):
        if self.closed:
            raise RuntimeError("pipeline disposed")
        # A reset to an older generation of the same instrument would
        # resurrect frames from an obsolete UI surface.
        if (epoch == self.swapchain.epoch and
                surface_generation < self.swapchain.generation):
            raise ValueError("surface generation must not decrease")
        self.jobs.invalidate()
        self.mailbox.reset(epoch, surface_generation)
        self.swapchain.reset(epoch, surface_generation, retain_front=retain_front)
        self.last_version = -1
        self.last_revision = None

    def offer(self, model: RenderModel):
        if self.closed:
            return False
        if not isinstance(model, RenderModel):
            raise ValueError("invalid render model")
        revision = self._revision(model)
        if self.last_revision is not None and revision < self.last_revision:
            return False
        if (self.mailbox.pending is not None
                and revision < self._revision(self.mailbox.pending)):
            return False
        return self.mailbox.offer(model)

    @staticmethod
    def _revision(model):
        # The book revision is primary. Equal books may still need redraw
        # after a viewport, style or DPI change.
        key = model.key
        return (key.book_version, key.view_version,
                key.style_version, key.dpi_version)

    def pump(self, now, visible=True):
        decision = self.mailbox.take(now, visible=visible)
        if decision.model is None:
            return PumpResult(decision.reason, False)
        model = decision.model
        revision = self._revision(model)
        if self.last_revision is not None and revision < self.last_revision:
            return PumpResult("STALE_RENDER_REVISION", False)
        generation = self.jobs.generation
        try:
            frame = rasterize(model)
        except (ValueError, OverflowError, MemoryError):
            self.failed_renders += 1
            return PumpResult("RASTER_FAILED", False)
        if (self.closed or generation != self.jobs.generation or
                model.key.epoch != self.swapchain.epoch or
                model.key.surface_generation != self.swapchain.generation):
            return PumpResult("STALE_AFTER_RASTER", False)
        if self.last_revision is not None and revision < self.last_revision:
            return PumpResult("STALE_AFTER_RASTER", False)
        if not self.swapchain.publish(frame):
            return PumpResult("STALE_SURFACE", False)
        self.last_version = model.key.book_version
        self.last_revision = revision
        self.renders += 1
        return PumpResult("PUBLISHED", True)

    def snapshot(self):
        return self.swapchain.snapshot()

    def dispose(self):
        self.jobs.close()
        self.mailbox.dispose()
        self.swapchain.dispose()
        self.closed = True

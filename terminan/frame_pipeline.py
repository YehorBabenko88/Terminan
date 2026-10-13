"""Pure synchronous DOM frame pipeline; no UI, threads, or exchange I/O.

Callers serialize reset/offer/pump/dispose on the UI owner thread.
A real UI adapter must marshal callbacks to that thread.
"""
from dataclasses import dataclass
from .frame_scheduler import LatestFrameMailbox
from .canvas_backend import FrameSwapchain, rasterize
from .render_model import RenderModel


@dataclass(frozen=True)
class PumpResult:
    reason: str
    published: bool


class DomFramePipeline:
    """One pending model and one immutable published RGBA buffer."""

    def __init__(self, fps=60):
        self.mailbox = LatestFrameMailbox(fps)
        self.swapchain = FrameSwapchain()
        self.closed = False
        self.last_version = -1
        self.renders = 0
        self.failed_renders = 0

    def reset(self, epoch, surface_generation=0):
        if self.closed:
            raise RuntimeError("pipeline disposed")
        self.mailbox.reset(epoch, surface_generation)
        self.swapchain.reset(epoch, surface_generation)
        self.last_version = -1

    def offer(self, model: RenderModel):
        if self.closed:
            return False
        if not isinstance(model, RenderModel):
            raise ValueError("invalid render model")
        if model.key.book_version < self.last_version:
            return False
        if (self.mailbox.pending is not None
                and model.key.book_version < self.mailbox.pending.key.book_version):
            return False
        return self.mailbox.offer(model)

    def pump(self, now, visible=True):
        decision = self.mailbox.take(now, visible=visible)
        if decision.model is None:
            return PumpResult(decision.reason, False)
        model = decision.model
        if model.key.book_version < self.last_version:
            return PumpResult("STALE_BOOK_VERSION", False)
        try:
            frame = rasterize(model)
        except (ValueError, OverflowError, MemoryError):
            self.failed_renders += 1
            return PumpResult("RASTER_FAILED", False)
        if not self.swapchain.publish(frame):
            return PumpResult("STALE_SURFACE", False)
        self.last_version = model.key.book_version
        self.renders += 1
        return PumpResult("PUBLISHED", True)

    def snapshot(self):
        return self.swapchain.snapshot()

    def dispose(self):
        self.mailbox.dispose()
        self.swapchain.dispose()
        self.closed = True

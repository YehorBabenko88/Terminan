"""Bounded latest-frame scheduling. Pure Python, deterministic, no UI callbacks."""
from dataclasses import dataclass
from .render_model import RenderModel


@dataclass(frozen=True)
class FrameDecision:
    model: RenderModel | None
    reason: str


class LatestFrameMailbox:
    """One pending immutable model; stale generations never reach presentation.

    The UI integration is responsible for scheduling at most one callback.
    The mailbox never coalesces or drops exchange/book updates.
    """

    def __init__(self, fps=60):
        if type(fps) not in (int, float) or not 1 <= fps <= 240:
            raise ValueError("fps out of range")
        self.period = 1.0 / fps
        self.next_allowed = 0.0
        self.pending = None
        self.epoch = None
        self.surface_generation = 0
        self.disposed = False
        self.replacements = 0
        self.stale_drops = 0

    def reset(self, epoch, surface_generation=0):
        if self.disposed:
            raise RuntimeError("mailbox disposed")
        if type(surface_generation) is not int or surface_generation < 0:
            raise ValueError("invalid surface generation")
        self.epoch = epoch
        self.surface_generation = surface_generation
        self.pending = None
        self.next_allowed = 0.0

    def offer(self, model: RenderModel):
        if self.disposed:
            return False
        if not isinstance(model, RenderModel):
            raise ValueError("invalid frame")
        if (model.key.epoch != self.epoch or
                model.key.surface_generation != self.surface_generation):
            self.stale_drops += 1
            return False
        if self.pending is not None:
            self.replacements += 1
        self.pending = model
        return True

    def take(self, now, visible=True):
        if self.disposed:
            return FrameDecision(None, "DISPOSED")
        if type(now) not in (int, float) or now < 0 or now != now:
            raise ValueError("invalid monotonic time")
        if not visible:
            return FrameDecision(None, "HIDDEN")
        if now < self.next_allowed:
            return FrameDecision(None, "FPS_LIMIT")
        if self.pending is None:
            return FrameDecision(None, "EMPTY")
        model = self.pending
        self.pending = None
        self.next_allowed = now + self.period
        return FrameDecision(model, "READY")

    def dispose(self):
        self.pending = None
        self.disposed = True

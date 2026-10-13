"""Bounded, immutable software frame buffers for a future UI canvas adapter.

This is a deterministic CPU rasterizer, not a GPU or platform-native canvas.
Only the latest completed frame is retained; no exchange data is modified.
"""
from dataclasses import dataclass
from threading import RLock
from .render_model import RenderModel, RenderKey

MAX_PIXELS = 32_000_000
MAX_BYTES = MAX_PIXELS * 4


@dataclass(frozen=True)
class RasterFrame:
    key: RenderKey
    width: int
    height: int
    rgba: bytes

    def __post_init__(self):
        if type(self.width) is not int or type(self.height) is not int:
            raise ValueError("invalid surface dimensions")
        if not 0 < self.width <= 16384 or not 0 < self.height <= 16384:
            raise ValueError("surface dimensions out of range")
        if self.width * self.height > MAX_PIXELS or len(self.rgba) != self.width * self.height * 4:
            raise ValueError("invalid pixel buffer")


def rasterize(model: RenderModel, *, background=(15, 20, 29, 255),
              bid_color=(28, 135, 105, 255), ask_color=(170, 65, 75, 255)):
    """Draw proportional bid/ask volume bars in a fresh owned RGBA byte buffer.

    Rows outside the surface are clipped. The backend does not draw text or
    invent order-book levels; it only consumes the immutable render model.
    """
    if not isinstance(model, RenderModel):
        raise ValueError("invalid render model")
    colors = (background, bid_color, ask_color)
    for color in colors:
        if (not isinstance(color, tuple) or len(color) != 4 or
                any(type(v) is not int or not 0 <= v <= 255 for v in color)):
            raise ValueError("invalid RGBA color")
    width, height = model.pixel_width, model.pixel_height
    if (type(width) is not int or type(height) is not int or
            width < 1 or height < 1 or width > 16384 or height > 16384 or
            width * height > MAX_PIXELS):
        raise ValueError("invalid surface budget")
    pixels = bytearray(bytes(background) * (width * height))
    max_volume = max((max(row.bid_lots, row.ask_lots) for row in model.rows), default=0)
    if max_volume > 0:
        half = width // 2
        for index, row in enumerate(model.rows):
            y0 = int(row.y_dip * model.scale_y)
            y1 = int((row.y_dip + model.row_height_dip) * model.scale_y)
            if y1 <= 0 or y0 >= height:
                continue
            for y in range(max(0, y0), min(height, y1)):
                if row.bid_lots > 0 and half > 0:
                    span = min(half, (row.bid_lots * half + max_volume - 1) // max_volume)
                    start, end, color = half - span, half, bytes(bid_color)
                    pixels[(y * width + start) * 4:(y * width + end) * 4] = color * (end - start)
                if row.ask_lots > 0 and width - half > 0:
                    span = min(width - half, (row.ask_lots * (width - half) + max_volume - 1) // max_volume)
                    start, end, color = half, half + span, bytes(ask_color)
                    pixels[(y * width + start) * 4:(y * width + end) * 4] = color * (end - start)
    return RasterFrame(model.key, width, height, bytes(pixels))


class FrameSwapchain:
    """Publish a completed immutable frame only for the active surface generation."""

    def __init__(self):
        self._lock = RLock()
        self.epoch = None
        self.generation = 0
        self.front = None
        self.closed = False
        self.dropped = 0
        self.retained_on_resize = 0

    def reset(self, epoch, generation, *, retain_front=False):
        with self._lock:
            if self.closed:
                raise RuntimeError("swapchain disposed")
            if type(generation) is not int or generation < 0:
                raise ValueError("invalid generation")
            old_front = self.front
            self.epoch, self.generation = epoch, generation
            if retain_front and old_front is not None and old_front.key.epoch == epoch:
                self.front = old_front
                self.retained_on_resize += 1
            else:
                self.front = None

    def publish(self, frame: RasterFrame):
        with self._lock:
            if self.closed:
                return False
            if not isinstance(frame, RasterFrame):
                raise ValueError("invalid raster frame")
            if frame.key.epoch != self.epoch or frame.key.surface_generation != self.generation:
                self.dropped += 1
                return False
            if (self.front is not None and
                    self.front.key.surface_generation == self.generation):
                old = self.front.key
                new = frame.key
                if ((new.book_version, new.view_version, new.style_version, new.dpi_version)
                        < (old.book_version, old.view_version, old.style_version, old.dpi_version)):
                    self.dropped += 1
                    return False
            self.front = frame
            return True

    def snapshot(self):
        with self._lock:
            return None if self.closed else self.front

    def dispose(self):
        with self._lock:
            self.front = None
            self.closed = True

"""Immutable DOM render projections; no native graphics or exchange dependencies."""
from dataclasses import dataclass
from math import ceil, isfinite
from .dom import BookView, viewport


@dataclass(frozen=True)
class RenderKey:
    epoch: str | None
    book_version: int
    view_version: int
    style_version: int
    dpi_version: int
    surface_generation: int


@dataclass(frozen=True)
class RenderRow:
    price_ticks: int
    y_dip: float
    bid_lots: int
    ask_lots: int


@dataclass(frozen=True)
class RenderModel:
    key: RenderKey
    status: str
    rows: tuple[RenderRow, ...]
    row_height_dip: float
    pixel_width: int
    pixel_height: int
    scale_y: float = 1.0

    def hit_test(self, y_dip: float):
        if (type(y_dip) not in (int, float) or
                not isfinite(y_dip) or y_dip < 0):
            return None
        index = int(y_dip // self.row_height_dip)
        return self.rows[index].price_ticks if 0 <= index < len(self.rows) else None


def build_render_model(view: BookView, *, top_tick: int, row_count: int,
                       group_ticks: int = 1, group_anchor: int = 0,
                       row_height_dip: float = 20.0, width_dip: float = 500.0,
                       height_dip: float = 500.0, scale_x: float = 1.0,
                       scale_y: float = 1.0, view_version: int = 0,
                       style_version: int = 0, dpi_version: int = 0,
                       surface_generation: int = 0) -> RenderModel:
    """Capture a single BookView; never mutate the book or UI objects."""
    for value in (row_height_dip, width_dip, height_dip, scale_x, scale_y):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value) or value <= 0:
            raise ValueError("invalid render dimensions")
    for value in (view_version, style_version, dpi_version, surface_generation):
        if type(value) is not int or value < 0:
            raise ValueError("invalid render generation")
    scaled_width, scaled_height = width_dip * scale_x, height_dip * scale_y
    if not isfinite(scaled_width) or not isfinite(scaled_height):
        raise ValueError("surface dimensions overflow")
    pixel_width, pixel_height = ceil(scaled_width), ceil(scaled_height)
    if not 0 < pixel_width <= 16384 or not 0 < pixel_height <= 16384:
        raise ValueError("surface exceeds pixel limits")
    if pixel_width * pixel_height > 32_000_000:
        raise ValueError("surface exceeds pixel budget")
    visible = viewport(view, top_tick, row_count, group_ticks, group_anchor)
    rows = tuple(RenderRow(row["price_ticks"], index * row_height_dip,
                           row["bid_lots"], row["ask_lots"])
                 for index, row in enumerate(visible))
    return RenderModel(RenderKey(view.epoch, view.version, view_version, style_version,
                                 dpi_version, surface_generation),
                       view.status.value, rows, float(row_height_dip),
                       pixel_width, pixel_height, float(scale_y))

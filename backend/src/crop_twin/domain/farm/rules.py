"""Pure farm validation and unit conversion, with no framework dependencies."""

import math
from datetime import date
from decimal import Decimal
from typing import Literal

from crop_twin.domain.farm.models import EventInput, PlotInput, Season


class FarmError(Exception):
    """A safe, actionable business error with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class FarmNotFound(FarmError):
    """The referenced farm resource does not exist."""


class FarmConflict(FarmError):
    """A concurrent or stale operation conflicts with existing farm records."""


def validate_plot(data: PlotInput) -> None:
    """Reject blank names, invalid manual area, and non-finite WGS84 positions."""
    if not data.name.strip() or len(data.name.strip()) > 80:
        raise FarmError("INVALID_PLOT_NAME", "地块名称应为 1–80 个字符")
    if not data.area_mu.is_finite() or not Decimal(0) < data.area_mu <= Decimal(1_000_000):
        raise FarmError("INVALID_AREA", "请填写大于 0 的地块面积（亩）")
    if not math.isfinite(data.latitude) or not -90 <= data.latitude <= 90:
        raise FarmError("INVALID_LATITUDE", "纬度应在 -90 到 90 之间")
    if not math.isfinite(data.longitude) or not -180 <= data.longitude <= 180:
        raise FarmError("INVALID_LONGITUDE", "经度应在 -180 到 180 之间")


def validate_season_dates(start: date, end: date | None) -> None:
    """Require an inclusive season end no earlier than its establishment date."""
    if end is not None and end < start:
        raise FarmError("INVALID_SEASON_DATES", "结束日期不能早于播种或移栽日期")


def seasons_overlap(start: date, end: date | None, other: Season) -> bool:
    """Check inclusive date intervals, treating an open season as unbounded."""
    return start <= (other.end_date or date.max) and other.start_date <= (end or date.max)


def validate_event_date(occurred_on: date, season: Season) -> None:
    """Keep management operations inside the recorded season interval."""
    if occurred_on < season.start_date:
        raise FarmError("EVENT_BEFORE_SEASON", "农事日期不能早于该季播种或移栽日期")
    if season.end_date is not None and occurred_on > season.end_date:
        raise FarmError("EVENT_AFTER_SEASON", "农事日期不能晚于该季结束日期")


def normalize_event_quantity(
    data: EventInput, area_ha: Decimal
) -> tuple[Decimal | None, Literal["mm", "kg/ha"] | None]:
    """Convert irrigation/application mass; never infer infiltration or pure nitrogen."""
    if data.event_type not in ("irrigation", "fertilization"):
        if data.quantity is not None or data.unit is not None or data.material_name:
            raise FarmError("UNEXPECTED_QUANTITY", "此类农事只需日期和备注，不填写水肥数量")
        return None, None
    if data.quantity is None or data.unit is None:
        raise FarmError("QUANTITY_REQUIRED", "请填写数量并选择单位")
    if not data.quantity.is_finite() or not Decimal(0) < data.quantity <= Decimal(1_000_000):
        raise FarmError("INVALID_QUANTITY", "数量必须大于 0 且不超过 1000000")
    if data.event_type == "irrigation":
        if data.unit not in ("mm", "m3") or data.material_name:
            raise FarmError("INVALID_IRRIGATION_UNIT", "灌溉单位请选择毫米或立方米，不填写肥料名称")
        quantity = data.quantity if data.unit == "mm" else data.quantity / (area_ha * Decimal(10))
        return quantity.quantize(Decimal("0.000001")), "mm"
    if data.unit not in ("kg/mu", "kg/ha"):
        raise FarmError("INVALID_FERTILIZER_UNIT", "施肥单位请选择千克/亩或千克/公顷")
    if not data.material_name or not data.material_name.strip():
        raise FarmError("MATERIAL_REQUIRED", "请填写肥料名称，例如尿素或复合肥")
    quantity = data.quantity * (Decimal(15) if data.unit == "kg/mu" else Decimal(1))
    return quantity.quantize(Decimal("0.000001")), "kg/ha"

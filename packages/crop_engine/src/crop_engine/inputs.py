"""Pure, offline input preflight for WOFOST72; it does not run or validate a crop model."""

import csv
import hashlib
import io
import json
import math
import re
from datetime import date, timedelta
from typing import TypedDict

type ParameterValue = float | list[float]


class InputDataError(ValueError):
    """A safe data error suitable for an import form."""


class WeatherDay(TypedDict):
    """Explicit measurement units; wind is measured at two metres."""

    date: str
    tmin_c: float
    tmax_c: float
    rain_mm: float
    radiation_mj_m2: float
    wind_m_s: float
    vapor_kpa: float


class Issue(TypedDict):
    """Stable preflight issue with plain-language explanation."""

    code: str
    message: str


class InputReport(TypedDict):
    """Input completeness is separate from engine availability and scientific validity."""

    input_ready: bool
    simulation_available: bool
    blocking_issues: list[Issue]
    warnings: list[Issue]
    missing_weather_days: int
    missing_parameters: list[str]


# Audited against PCSE 6.0.13 WOFOST72 component ParameterTemplate declarations.
# Calendar injects CROP_START_TYPE/CROP_END_TYPE; the soil supplies SM0/SMFCF/SMW/RDMSOL.
TABLE_PARAMETERS = frozenset(
    "AMAXTB EFFTB KDIFTB TMNFTB TMPFTB RFSETB FLTB FOTB FRTB FSTB SLATB "
    "RDRSTB SSATB RDRRTB DTSMTB".split()
)
SCALAR_PARAMETERS = frozenset(
    "CVL CVO CVR CVS Q10 RML RMO RMR RMS CFET CRAIRC DEPNR IAIRDU IOX PERDL "
    "RGRLAI SPAN TBASE TDWI RDI RDMCR RRI SPA DLC DLO DVSEND DVSI IDSL "
    "TBASEM TEFFMX TSUM1 TSUM2 TSUMEM".split()
)
WEATHER_COLUMNS = (
    "date",
    "tmin_c",
    "tmax_c",
    "rain_mm",
    "radiation_mj_m2",
    "wind_m_s",
    "vapor_kpa",
)


def canonical_json(payload: object) -> str:
    """Serialize portable JSON deterministically, without NaN or hidden conversions."""
    return json.dumps(
        _portable_numbers(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _portable_numbers(value: object) -> object:
    # JSON.parse/stringify turns 1.0 into 1. Hash the same number identically after export.
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {key: _portable_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_portable_numbers(item) for item in value]
    return value


def content_hash(payload: object) -> str:
    """Compute the SHA-256 of the exact canonical payload, not a filename."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_parameters(parameters: dict[str, ParameterValue]) -> None:
    """Reject executable/oversized/non-finite values and malformed interpolation tables."""
    if not 1 <= len(parameters) <= 150:
        raise InputDataError("品种参数应为 1–150 个数值或数值数组")
    for key, value in parameters.items():
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,39}", key):
            raise InputDataError("参数名称应为大写字母、数字和下划线")
        values = value if isinstance(value, list) else [value]
        if not 1 <= len(values) <= 200 or any(
            isinstance(number, bool)
            or not isinstance(number, (float, int))
            or not math.isfinite(number)
            for number in values
        ):
            raise InputDataError(f"参数 {key} 必须使用有限数值，数组最多 200 项")
        if key in TABLE_PARAMETERS or key == "VERNRTB":
            if not isinstance(value, list) or len(value) < 4 or len(value) % 2:
                raise InputDataError(f"参数 {key} 应为至少两组横轴/纵轴数值")
            if any(left >= right for left, right in zip(value[::2], value[2::2], strict=False)):
                raise InputDataError(f"参数 {key} 的横轴必须严格递增")
        if key in SCALAR_PARAMETERS and isinstance(value, list):
            raise InputDataError(f"参数 {key} 应为单个数值")
    for key in ("TSUM1", "TSUM2", "TDWI", "SPAN", "RDI", "RDMCR", "CVL", "CVO", "CVR", "CVS"):
        scalar = parameters.get(key)
        if isinstance(scalar, (int, float)) and scalar <= 0:
            raise InputDataError(f"参数 {key} 应大于零")
    for key, allowed in (("IDSL", (0, 1, 2)), ("IAIRDU", (0, 1)), ("IOX", (0, 1))):
        if key in parameters and parameters[key] not in allowed:
            raise InputDataError(f"参数 {key} 的取值不符合 WOFOST72 输入范围")


def parse_weather_csv(text: str) -> list[WeatherDay]:
    """Read a bounded UTF-8 CSV with explicit units; never fill missing observations."""
    if len(text.encode("utf-8")) > 262144:
        raise InputDataError("天气 CSV 最多 256 KiB")
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), strict=True)
    try:
        fieldnames = reader.fieldnames
    except csv.Error:
        raise InputDataError("天气 CSV 表头格式不正确") from None
    if (
        fieldnames is None
        or len(fieldnames) != len(WEATHER_COLUMNS)
        or set(fieldnames) != set(WEATHER_COLUMNS)
    ):
        raise InputDataError("天气列应为 " + ",".join(WEATHER_COLUMNS))
    days: list[WeatherDay] = []
    dates: set[date] = set()
    try:
        for index, row in enumerate(reader, start=2):
            if len(days) >= 366:
                raise InputDataError("一次最多导入 366 天天气")
            if None in row or any(value is None for value in row.values()):
                raise InputDataError(f"第 {index} 行列数不正确")
            measured = date.fromisoformat(row["date"].strip())
            values = [float(row[key]) for key in WEATHER_COLUMNS[1:]]
            if measured in dates:
                raise InputDataError(f"第 {index} 行日期重复")
            if measured > date.today():
                raise InputDataError(f"第 {index} 行为未来日期，请导入已发生的天气")
            if any(not math.isfinite(value) for value in values):
                raise InputDataError(f"第 {index} 行含空值或非有限数值")
            tmin, tmax, rain, radiation, wind, vapor = values
            if tmin > tmax or not -90 <= tmin <= tmax <= 65:
                raise InputDataError(f"第 {index} 行最低/最高温度不正确")
            if any(value < 0 for value in (rain, radiation, wind, vapor)):
                raise InputDataError(f"第 {index} 行雨量、辐射、风速和蒸汽压不能为负")
            if rain > 10000 or radiation > 100 or wind > 200 or vapor > 25:
                raise InputDataError(f"第 {index} 行天气数值过大，请检查单位")
            dates.add(measured)
            days.append(
                WeatherDay(
                    date=measured.isoformat(),
                    tmin_c=tmin,
                    tmax_c=tmax,
                    rain_mm=rain,
                    radiation_mj_m2=radiation,
                    wind_m_s=wind,
                    vapor_kpa=vapor,
                )
            )
    except (ValueError, csv.Error, TypeError) as error:
        if isinstance(error, InputDataError):
            raise
        raise InputDataError("天气 CSV 日期或数值格式不正确，请核对每一行") from None
    if not days:
        raise InputDataError("天气 CSV 至少需要一天记录")
    return sorted(days, key=lambda day: day["date"])


def pcse_weather_fields(day: WeatherDay) -> dict[str, str | float]:
    """Convert observed units to PCSE fields; E0/ES0/ET0 await engine-side calculation."""
    return {
        "DAY": day["date"],
        "TMIN": day["tmin_c"],
        "TMAX": day["tmax_c"],
        "RAIN": day["rain_mm"] / 10,
        "IRRAD": day["radiation_mj_m2"] * 1_000_000,
        "WIND": day["wind_m_s"],
        "VAP": day["vapor_kpa"] * 10,
    }


def check_inputs(
    parameters: dict[str, ParameterValue],
    days: list[WeatherDay],
    start: date,
    end: date,
    establishment_method: str,
) -> InputReport:
    """Check a contiguous observed period and core parameters; report every missing day."""
    required = SCALAR_PARAMETERS | TABLE_PARAMETERS
    if parameters.get("IDSL") == 2:
        required |= {"VERNBASE", "VERNDVS", "VERNSAT", "VERNRTB"}
    missing = sorted(required - parameters.keys())
    observed = {day["date"] for day in days}
    absent = [
        (start + timedelta(days=offset)).isoformat()
        for offset in range((end - start).days + 1)
        if (start + timedelta(days=offset)).isoformat() not in observed
    ]
    issues: list[Issue] = []
    if missing:
        issues.append(
            Issue(code="MISSING_PARAMETERS", message="品种参数缺少：" + ", ".join(missing))
        )
    if absent:
        issues.append(
            Issue(
                code="WEATHER_GAPS", message=f"缺少 {len(absent)} 天天气：" + ", ".join(absent[:10])
            )
        )
    if establishment_method == "transplanting":
        issues.append(
            Issue(code="TRANSPLANT_ADAPTER_PENDING", message="移栽初始状态与育秧过程尚待模型适配")
        )
    if any(
        day["tmin_c"] < -50
        or day["tmax_c"] > 60
        or day["rain_mm"] > 250
        or day["radiation_mj_m2"] > 40
        or not 0.006 <= day["vapor_kpa"] <= 19.93
        or day["wind_m_s"] > 100
        for day in days
        if start.isoformat() <= day["date"] <= end.isoformat()
    ):
        issues.append(
            Issue(
                code="PCSE_WEATHER_RANGE",
                message="天气含超出 PCSE 标准范围的值，原值已保留，请核对",
            )
        )
    return InputReport(
        input_ready=not issues,
        simulation_available=False,
        blocking_issues=issues,
        missing_weather_days=len(absent),
        missing_parameters=missing,
        warnings=[
            Issue(code="LOCAL_VALIDATION_PENDING", message="品种与土壤参数尚需当地实测验证"),
            Issue(
                code="MANAGEMENT_MAPPING_PENDING",
                message="农事已封存，灌溉和施肥尚未转换为模型管理信号",
            ),
        ],
    )

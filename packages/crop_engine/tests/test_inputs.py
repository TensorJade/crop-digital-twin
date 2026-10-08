"""Offline data checks are repeatable and do not pretend to validate crop performance."""

import hashlib
from datetime import date, timedelta

import pytest
from crop_engine.inputs import (
    SCALAR_PARAMETERS,
    TABLE_PARAMETERS,
    WEATHER_COLUMNS,
    InputDataError,
    canonical_json,
    check_inputs,
    content_hash,
    parse_weather_csv,
    pcse_weather_fields,
    validate_parameters,
)

HEADER = ",".join(WEATHER_COLUMNS)
LINE = "2026-03-02,20,30,10,15,2,1.5"


def test_original_units_convert_to_pcse_without_changing_the_observation() -> None:
    day = parse_weather_csv(HEADER + "\n" + LINE)[0]
    original = dict(day)
    assert pcse_weather_fields(day) == {
        "DAY": "2026-03-02",
        "TMIN": 20,
        "TMAX": 30,
        "RAIN": 1,
        "IRRAD": 15_000_000,
        "WIND": 2,
        "VAP": 15,
    }
    assert day == original
    assert "ET0" not in pcse_weather_fields(day)


def test_hash_is_canonical_utf8_and_rejects_non_json_numbers() -> None:
    first = {"品种": "测试用", "values": [1, 2]}
    assert canonical_json(first) == '{"values":[1,2],"品种":"测试用"}'
    assert content_hash(first) == content_hash({"values": [1, 2], "品种": "测试用"})
    assert content_hash(first) == hashlib.sha256(canonical_json(first).encode()).hexdigest()
    with pytest.raises(ValueError):
        content_hash({"bad": float("nan")})
    assert content_hash({"nested": [1.0, -0.0, {"tmin": 20.0}]}) == content_hash(
        {"nested": [1, 0, {"tmin": 20}]}
    )


@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {"bad key": 1},
        {"TSUM1": float("nan")},
        {"TSUM2": True},
        {"AMAXTB": [0, 1, 0, 2]},
        {"AMAXTB": [0, 1, 2]},
        {"AMAXTB": 1},
        {"TDWI": [1, 2]},
        {"TDWI": -1},
        {"IDSL": 3},
        {"IOX": 2},
        {"UNKNOWN": [1] * 201},
        {f"K{index}": 1 for index in range(151)},
    ],
)
def test_bad_parameter_shapes_never_enter_the_model_input(parameters) -> None:
    with pytest.raises(InputDataError):
        validate_parameters(parameters)


@pytest.mark.parametrize(
    "text",
    [
        "date,tmin_c\n2026-03-02,20",
        '"unterminated',
        HEADER,
        HEADER + "\n" + LINE + "\n" + LINE,
        HEADER + "\n2026-03-02,30,20,10,15,2,1.5",
        HEADER + "\n2026-03-02,20,30,-1,15,2,1.5",
        HEADER + "\n2026-03-02,20,30,nan,15,2,1.5",
        HEADER + "\n2026-03-02,20,30,10,15,2",
        HEADER + "\n" + LINE + ",extra",
        HEADER + "\n2026-03-02,20,30,10,15,2,1e308",
        HEADER + "\nnot-a-date,20,30,10,15,2,1.5",
        HEADER + "\n" + (date.today() + timedelta(days=1)).isoformat() + ",20,30,10,15,2,1.5",
        HEADER + ",date\n" + LINE + ",2026-03-02",
    ],
)
def test_bad_weather_is_reported_without_zero_fill(text: str) -> None:
    with pytest.raises(InputDataError):
        parse_weather_csv(text)


def test_csv_byte_and_day_limits_and_bom_are_explicit() -> None:
    assert parse_weather_csv("\ufeff" + HEADER + "\r\n" + LINE)[0]["rain_mm"] == 10
    with pytest.raises(InputDataError, match="256 KiB"):
        parse_weather_csv("汉" * 90000)
    text = (
        HEADER
        + "\n"
        + "\n".join(
            (date(2024, 1, 1) + timedelta(days=index)).isoformat() + ",20,30,10,15,2,1.5"
            for index in range(367)
        )
    )
    with pytest.raises(InputDataError, match="366"):
        parse_weather_csv(text)


def test_complete_static_inputs_are_distinct_from_simulation_availability() -> None:
    # Synthetic structural test values, never a real rice cultivar or a scientific benchmark.
    parameters = {key: 1.0 for key in SCALAR_PARAMETERS}
    parameters.update({key: [0.0, 1.0, 2.0, 1.0] for key in TABLE_PARAMETERS})
    parameters["IDSL"] = 0.0
    validate_parameters(parameters)
    days = parse_weather_csv(HEADER + "\n" + LINE)
    report = check_inputs(parameters, days, date(2026, 3, 2), date(2026, 3, 2), "direct_sowing")
    assert report["input_ready"] is True
    assert report["simulation_available"] is False
    assert report["warnings"]
    parameters["IDSL"] = 2.0
    report = check_inputs(parameters, days, date(2026, 3, 2), date(2026, 3, 4), "transplanting")
    assert report["missing_weather_days"] == 2
    assert set(report["missing_parameters"]) == {"VERNBASE", "VERNDVS", "VERNSAT", "VERNRTB"}
    assert {issue["code"] for issue in report["blocking_issues"]} == {
        "WEATHER_GAPS",
        "MISSING_PARAMETERS",
        "TRANSPLANT_ADAPTER_PENDING",
    }


def test_extreme_real_weather_is_preserved_but_blocked_for_the_standard_pcse_range() -> None:
    days = parse_weather_csv(HEADER + "\n2026-03-02,20,30,300,45,2,1.5")
    report = check_inputs({"TSUM1": 800}, days, date(2026, 3, 2), date(2026, 3, 2), "direct_sowing")
    assert "PCSE_WEATHER_RANGE" in {issue["code"] for issue in report["blocking_issues"]}
    assert days[0]["rain_mm"] == 300


@pytest.mark.parametrize(
    "vapor,blocked", [(0, True), (0.006, False), (19.91, False), (19.93, False), (19.94, True)]
)
def test_pcse_vapor_limits_are_checked_in_kpa(vapor: float, blocked: bool) -> None:
    days = parse_weather_csv(HEADER + f"\n2026-03-02,20,30,10,15,2,{vapor}")
    report = check_inputs({"TSUM1": 800}, days, date(2026, 3, 2), date(2026, 3, 2), "direct_sowing")
    assert (
        "PCSE_WEATHER_RANGE" in {issue["code"] for issue in report["blocking_issues"]}
    ) is blocked

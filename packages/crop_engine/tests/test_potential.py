"""Real PCSE kernel checks use a declared synthetic fixture, never a farm default."""

import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from crop_engine.inputs import InputDataError
from crop_engine.potential import SimulationFailure, run_isolated, validate_potential_input

FIXTURE = Path(__file__).resolve().parents[3] / "tests/fixtures/potential-input.json"


@pytest.fixture
def payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_real_pcse_is_repeatable_and_does_not_import_in_parent_or_touch_user_config(payload):
    pcse_folder = Path.home() / ".pcse"
    before = {
        str(p): (p.stat().st_size, p.stat().st_mtime_ns)
        for p in pcse_folder.rglob("*")
        if p.is_file()
    }
    first, second = run_isolated(payload), run_isolated(payload)
    assert first == second
    assert "pcse" not in sys.modules
    after = {
        str(p): (p.stat().st_size, p.stat().st_mtime_ns)
        for p in pcse_folder.rglob("*")
        if p.is_file()
    }
    assert before == after
    assert first["pcse_version"] == "6.0.13"
    assert first["simulation_executed"] is True and first["agronomically_validated"] is False
    assert first["management_effects_applied"] is False
    assert len(first["daily"]) == 15
    assert first["daily"][0]["lai"] == pytest.approx(0.224)
    assert first["daily"][-1]["dvs"] == pytest.approx(0.2625)
    assert first["daily"][-1]["above_ground_kg_ha"] > first["daily"][0]["above_ground_kg_ha"]
    assert 0 < first["reference_weather"][0]["ET0"] < 2.5
    assert first["units"]["ET0"] == "cm/day"


@pytest.mark.parametrize(
    "change",
    [
        ("schema_version", "2"),
        ("season.establishment_method", "transplanting"),
        ("assets.crop.payload.model_code", "unknown"),
        ("season.variety_name", "不匹配"),
        ("assets.crop.payload.parameters.TSUM1", -1),
        ("period.cutoff_date", "2027-01-01"),
        ("assets.weather.payload.days", []),
        ("assets.weather.payload.time_basis", "UTC"),
        ("assets.weather.payload.elevation_m", 7000),
        ("assets.weather.payload.angstrom_a", None),
        ("assets.weather.payload.angstrom_b", 0.8),
    ],
)
def test_preflight_rejects_unsupported_or_incomplete_inputs(payload, change):
    keys = change[0].split(".")
    target = payload
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = change[1]
    with pytest.raises(InputDataError):
        validate_potential_input(payload)


def test_one_day_is_a_real_initial_state_and_bad_partition_is_a_real_engine_error(payload):
    payload["period"]["cutoff_date"] = payload["period"]["emergence_date"]
    assert len(run_isolated(payload)["daily"]) == 1
    broken = copy.deepcopy(payload)
    broken["assets"]["crop"]["payload"]["parameters"]["FLTB"] = [0, 0.9, 2, 0.9]
    with pytest.raises(SimulationFailure, match="ENGINE_INPUT_REJECTED"):
        run_isolated(broken)


@pytest.mark.parametrize(
    "response,code",
    [
        (SimpleNamespace(returncode=1, stdout="secret"), "ENGINE_INPUT_REJECTED"),
        (SimpleNamespace(returncode=0, stdout="not json"), "ENGINE_OUTPUT_INVALID"),
        (SimpleNamespace(returncode=0, stdout='{"daily":[]}'), "ENGINE_OUTPUT_INVALID"),
        (SimpleNamespace(returncode=0, stdout="a" * 524289), "RESULT_TOO_LARGE"),
    ],
)
def test_subprocess_protocol_errors_remain_safe(payload, monkeypatch, response, code):
    import crop_engine.potential as module

    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: response)
    with pytest.raises(SimulationFailure, match=code):
        run_isolated(payload)


def test_timeout_and_process_failures_are_bounded(payload, monkeypatch):
    import subprocess

    import crop_engine.potential as module

    oversized = {**payload, "extra": "a" * 1048576}
    with pytest.raises(SimulationFailure, match="INPUT_TOO_LARGE"):
        run_isolated(oversized)

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("private", 0)

    monkeypatch.setattr(module.subprocess, "run", timeout)
    with pytest.raises(SimulationFailure, match="ENGINE_TIMEOUT"):
        run_isolated(payload)

    def unavailable(*args, **kwargs):
        raise OSError("private path")

    monkeypatch.setattr(module.subprocess, "run", unavailable)
    with pytest.raises(SimulationFailure, match="ENGINE_UNAVAILABLE"):
        run_isolated(payload)

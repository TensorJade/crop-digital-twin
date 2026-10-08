"""Potential production contracts, without importing PCSE into the API process."""

import json
import os
import subprocess
import sys
import tempfile
from datetime import date
from typing import Any, cast

from crop_engine.inputs import (
    InputDataError,
    ParameterValue,
    WeatherDay,
    canonical_json,
    check_inputs,
    validate_parameters,
)

PCSE_VERSION = "6.0.13"
MODEL_CODE = "WOFOST72_PP"
ADAPTER_VERSION = "1.0.0"
ASSUMPTIONS = [
    "潜在生长：假设水肥充足，未计算灌溉、施肥、病虫害和水田淹水的影响。",
    "只计算已发生天气覆盖的日期；不是未来天气预测或产量承诺。",
    "参数尚需当地实测验证；贮藏器官干物质不是实收稻谷产量。",
]


class SimulationFailure(Exception):
    """Stable worker failure category; private PCSE errors are never returned to users."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def validate_potential_input(payload: dict[str, Any]) -> None:
    """Recheck frozen input independently of its historic completeness report."""
    if payload.get("schema_version") != "1.0.0":
        raise InputDataError("输入快照版本不支持，请重新准备资料")
    season = payload["season"]
    crop = payload["assets"]["crop"]["payload"]
    weather = payload["assets"]["weather"]["payload"]
    if season["establishment_method"] != "direct_sowing":
        raise InputDataError("当前潜在生长计算仅支持直播；移栽育秧尚待适配")
    if crop["crop_code"] != "rice" or crop["model_code"] != "WOFOST72":
        raise InputDataError("当前仅支持 rice/WOFOST72 品种参数")
    if season["variety_name"] and season["variety_name"] != crop["variety_name"]:
        raise InputDataError("品种参数与种植季不一致")
    parameters = cast(dict[str, ParameterValue], crop["parameters"])
    validate_parameters(parameters)
    start = date.fromisoformat(payload["period"]["emergence_date"])
    end = date.fromisoformat(payload["period"]["cutoff_date"])
    if not start <= end <= date.today() or (end - start).days >= 366:
        raise InputDataError("模拟期间应为已发生的 1–366 天")
    report = check_inputs(
        parameters, cast(list[WeatherDay], weather["days"]), start, end, "direct_sowing"
    )
    if not report["input_ready"]:
        raise InputDataError("输入资料未补齐或超出模型范围，请重新检查并保存快照")
    if weather["time_basis"] != "Asia/Shanghai":
        raise InputDataError("当前计算需要按北京时间整理的逐日天气，请重新导入")
    if not -300 <= weather["elevation_m"] <= 6000:
        raise InputDataError("天气来源海拔超出 PCSE 标准范围")
    a, b = weather.get("angstrom_a"), weather.get("angstrom_b")
    if a is None or b is None:
        raise InputDataError("天气缺少蒸散计算系数 A/B，请由资料提供者补充后另存快照")
    if not 0.1 <= a <= 0.4 or not 0.3 <= b <= 0.7 or not 0.6 <= a + b <= 0.9:
        raise InputDataError("蒸散计算系数 A/B 不符合 PCSE 输入范围")


def run_isolated(payload: dict[str, Any], *, timeout_seconds: float = 60) -> dict[str, Any]:
    """Run bounded PCSE in a disposable process, with no DB URL or credential environment."""
    validate_potential_input(payload)
    data = canonical_json(payload)
    if len(data.encode("utf-8")) > 1048576:
        raise SimulationFailure("INPUT_TOO_LARGE")
    with tempfile.TemporaryDirectory(prefix="crop-twin-pcse-") as directory:
        # PCSE's get_user_home falls back to tempfile when USER/USERNAME are absent.
        # Keep only runtime necessities; no HOME, DB credentials, proxy or application secrets.
        environment = {
            key: value
            for key, value in os.environ.items()
            if key.upper()
            in {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "LANG", "LC_ALL"}
        }
        environment["CROP_TWIN_PCSE_SANDBOX"] = directory
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-X", "utf8", "-m", "crop_engine.pcse_runner"],
                input=data,
                encoding="utf-8",
                capture_output=True,
                timeout=timeout_seconds,
                cwd=directory,
                env=environment,
            )
        except subprocess.TimeoutExpired:
            raise SimulationFailure("ENGINE_TIMEOUT") from None
        except OSError:
            raise SimulationFailure("ENGINE_UNAVAILABLE") from None
        if completed.returncode != 0:
            raise SimulationFailure("ENGINE_INPUT_REJECTED")
        if len(completed.stdout.encode("utf-8")) > 524288:
            raise SimulationFailure("RESULT_TOO_LARGE")
        try:
            result = json.loads(completed.stdout)
            if (
                not isinstance(result, dict)
                or not isinstance(result.get("daily"), list)
                or not result["daily"]
            ):
                raise ValueError("Invalid engine response")
            canonical_json(result)
            return cast(dict[str, Any], result)
        except (ValueError, TypeError):
            raise SimulationFailure("ENGINE_OUTPUT_INVALID") from None

"""Private subprocess entrypoint: no HTTP, SQL, provider downloads or user configuration."""

import importlib
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from crop_engine.inputs import canonical_json, pcse_weather_fields
from crop_engine.potential import (
    ADAPTER_VERSION,
    ASSUMPTIONS,
    MODEL_CODE,
    PCSE_VERSION,
    validate_potential_input,
)


def initialize_runtime() -> None:
    """Contain the pinned PCSE import side effects, without changing the user's home."""
    sandbox = Path(os.environ["CROP_TWIN_PCSE_SANDBOX"]).resolve()
    if sandbox != Path.cwd().resolve() or not sandbox.name.startswith("crop-twin-pcse-"):
        raise ValueError("PCSE requires an isolated temporary directory")
    if "USER" in os.environ or "USERNAME" in os.environ:
        raise ValueError("PCSE runtime is not isolated")
    tempfile.tempdir = str(sandbox)
    configuration = sandbox / ".pcse"
    configuration.mkdir()
    sys.path.insert(0, str(configuration))
    (configuration / "user_settings.py").write_text(
        "LOG_CONFIG = {'version': 1, 'disable_existing_loggers': False, "
        "'handlers': {'null': {'class': 'logging.NullHandler'}}, "
        "'root': {'handlers': ['null'], 'level': 'ERROR'}}\n",
        encoding="utf-8",
    )
    # Suppress PCSE's automatic demo database creation; this empty marker is never queried.
    (configuration / "pcse.db").touch()


def calculate(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the real pinned WOFOST72_PP with declared weather coefficients and emergence."""
    validate_potential_input(payload)
    pcse = importlib.import_module("pcse")
    if pcse.__version__ != PCSE_VERSION:
        raise ValueError("Unexpected PCSE version")
    base = importlib.import_module("pcse.base")
    models = importlib.import_module("pcse.models")
    util = importlib.import_module("pcse.util")
    source = payload["assets"]["weather"]["payload"]
    start = date.fromisoformat(payload["period"]["emergence_date"])
    end = date.fromisoformat(payload["period"]["cutoff_date"])
    weather = base.WeatherDataProvider()
    weather.latitude, weather.longitude, weather.elevation = (
        source["latitude"],
        source["longitude"],
        source["elevation_m"],
    )
    weather.description = ["Frozen user-supplied observed weather; no external provider."]
    reference_weather = []
    for day in source["days"]:
        measured = date.fromisoformat(day["date"])
        if not start <= measured <= end:
            continue
        values: dict[str, Any] = dict(pcse_weather_fields(day))
        values["DAY"] = measured
        values.update(LAT=source["latitude"], LON=source["longitude"], ELEV=source["elevation_m"])
        e0, es0, et0 = util.reference_ET(
            DAY=measured,
            LAT=source["latitude"],
            ELEV=source["elevation_m"],
            TMIN=values["TMIN"],
            TMAX=values["TMAX"],
            IRRAD=values["IRRAD"],
            VAP=values["VAP"],
            WIND=values["WIND"],
            ANGSTA=source["angstrom_a"],
            ANGSTB=source["angstrom_b"],
            ETMODEL="PM",
        )
        values.update(E0=e0 / 10, ES0=es0 / 10, ET0=et0 / 10)
        weather._store_WeatherDataContainer(base.WeatherDataContainer(**values), measured)
        reference_weather.append({**values, "DAY": measured.isoformat()})
    crop = payload["assets"]["crop"]["payload"]
    parameters = base.ParameterProvider(
        cropdata=crop["parameters"], soildata=payload["pcse_fields"]["soil"]
    )
    management = [
        {
            start: {
                "CropCalendar": {
                    "crop_name": "rice",
                    "variety_name": crop["variety_name"],
                    "crop_start_date": start,
                    "crop_start_type": "emergence",
                    "crop_end_date": None,
                    "crop_end_type": "maturity",
                    "max_duration": 366,
                },
                "TimedEvents": None,
                "StateEvents": None,
            }
        }
    ]
    model = models.Wofost72_PP(
        parameters, weather, management, output_vars=["DVS", "LAI", "TAGP", "TWSO"]
    )
    if end > start:
        model.run_till(end)
    daily = [
        {
            "date": record["day"].isoformat(),
            "dvs": float(record["DVS"]),
            "lai": float(record["LAI"]),
            "above_ground_kg_ha": float(record["TAGP"]),
            "storage_organs_kg_ha": float(record["TWSO"]),
        }
        for record in model.get_output()
        if all(record[key] is not None for key in ("DVS", "LAI", "TAGP", "TWSO"))
    ]
    if not daily:
        raise ValueError("No crop output")
    return {
        "schema_version": "1.0.0",
        "model_code": MODEL_CODE,
        "pcse_version": PCSE_VERSION,
        "adapter_version": ADAPTER_VERSION,
        "simulation_executed": True,
        "agronomically_validated": False,
        "management_effects_applied": False,
        "assumptions": ASSUMPTIONS,
        "requested_period": payload["period"],
        "last_crop_date": daily[-1]["date"],
        "daily": daily,
        "weather_method": {
            "reference_et": "PCSE reference_ET / PM",
            "angstrom_a": source["angstrom_a"],
            "angstrom_b": source["angstrom_b"],
        },
        "reference_weather": reference_weather,
        "units": {
            "lai": "m2/m2",
            "above_ground_kg_ha": "kg dry matter/ha",
            "storage_organs_kg_ha": "kg dry matter/ha",
            "E0": "cm/day",
            "ES0": "cm/day",
            "ET0": "cm/day",
        },
    }


def main() -> None:
    """Read bounded JSON from stdin; expose only a failure code, never PCSE exception text."""
    try:
        initialize_runtime()
        data = sys.stdin.buffer.read(1048577)
        if len(data) > 1048576:
            raise ValueError("Input too large")
        payload = json.loads(data.decode("utf-8"))
        result = calculate(payload)
        sys.stdout.write(canonical_json(result))
    except Exception:
        sys.stderr.write("ENGINE_INPUT_REJECTED\n")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Prepare DJI Mavic 3M folders for an OpenDroneMap multispectral run.

The DJI single-band TIFFs in a raw flight folder commonly have no GeoTIFF
transform.  Their matching D.JPG contains the RTK position and camera pose,
so the photogrammetry engine must use the complete image group instead of
trying to mosaic TIFF pixels by filename or array position.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

GROUP_RE = re.compile(r"^(?P<stamp>DJI_\d{14})_(?P<index>\d{4})_D\.JPG$", re.IGNORECASE)
BANDS = ("G", "NIR", "R", "RE")
XMP_FIELDS = {
    "GpsLatitude": "latitude",
    "GpsLongitude": "longitude",
    "AbsoluteAltitude": "absolute_altitude_m",
    "RelativeAltitude": "relative_altitude_m",
    "GimbalYawDegree": "gimbal_yaw_deg",
    "GimbalPitchDegree": "gimbal_pitch_deg",
}


@dataclass(frozen=True)
class ImageGroup:
    group_id: str
    visible: str
    bands: dict[str, str]
    extra_visible: list[str]
    capture_time: str | None
    latitude: float | None
    longitude: float | None
    relative_altitude_m: float | None
    complete: bool
    missing: list[str]


def _read_xmp(path: Path) -> str:
    from PIL import Image

    with Image.open(path) as image:
        value = image.info.get("xmp", b"")
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)


def _xmp_value(xmp: str, name: str) -> str | None:
    match = re.search(rf'drone-dji:{name}="([^"]+)"', xmp)
    return match.group(1) if match else None


def _float_xmp(xmp: str, name: str) -> float | None:
    value = _xmp_value(xmp, name)
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def _group_id(path: Path) -> str:
    match = GROUP_RE.match(path.name)
    if not match:
        raise ValueError(f"不是 DJI D.JPG 文件: {path.name}")
    return f"{match.group('stamp')}_{match.group('index')}"


def discover_groups(flight_dir: Path) -> list[ImageGroup]:
    """Match each D.JPG to its four multispectral TIFFs without altering files."""
    groups: list[ImageGroup] = []
    for visible in sorted(flight_dir.glob("*_D.JPG")):
        group_id = _group_id(visible)
        prefix = visible.name[: -len("_D.JPG")]
        index = GROUP_RE.match(visible.name).group("index")
        bands = {}
        for band in BANDS:
            matches = list(flight_dir.glob(f"*_{index}_MS_{band}.TIF"))
            if len(matches) > 1:
                raise ValueError(f"重复拍摄序号: {index} {band}")
            bands[band] = matches[0].name if matches else f"{prefix}_MS_{band}.TIF"
        missing = [name for name in bands.values() if not (flight_dir / name).is_file()]
        extras = sorted(
            path.name for path in flight_dir.glob(f"{prefix}_*.JPG") if path.name != visible.name
        )
        xmp = _read_xmp(visible)
        timestamp = None
        from PIL import Image

        with Image.open(visible) as image:
            timestamp = image.getexif().get(306)
        fields: dict[str, float | None] = {}
        for source, target in XMP_FIELDS.items():
            fields[target] = _float_xmp(xmp, source)
        groups.append(
            ImageGroup(
                group_id=group_id,
                visible=visible.name,
                bands=bands,
                extra_visible=extras,
                capture_time=timestamp,
                latitude=fields["latitude"],
                longitude=fields["longitude"],
                relative_altitude_m=fields["relative_altitude_m"],
                complete=not missing,
                missing=missing,
            )
        )
    return groups


def _validate_tiff(path: Path) -> dict[str, object]:
    import rasterio

    with rasterio.open(path) as dataset:
        return {
            "width": dataset.width,
            "height": dataset.height,
            "count": dataset.count,
            "dtype": dataset.dtypes[0],
            "crs": dataset.crs.to_string() if dataset.crs else None,
            "transform": tuple(dataset.transform),
            "nodata": dataset.nodata,
        }


def _link_or_copy(source: Path, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.hardlink_to(source)
        return "hardlink"
    except (OSError, NotImplementedError):
        shutil.copy2(source, target)
        return "copy"


def _stage_flight(flight_dir: Path, output_dir: Path, groups: Iterable[ImageGroup]) -> str:
    mode = "hardlink"
    target = output_dir / "images"
    target.mkdir(parents=True, exist_ok=True)
    for group in groups:
        names = [group.visible, *group.bands.values()]
        for name in names:
            mode = _link_or_copy(flight_dir / name, target / name)
    return mode


def prepare_flight(
    flight_dir: Path, output_root: Path, *, allow_incomplete: bool = False
) -> dict[str, object]:
    groups = discover_groups(flight_dir)
    if not groups:
        raise ValueError(f"没有找到 *_D.JPG: {flight_dir}")
    incomplete = [group.group_id for group in groups if not group.complete]
    if incomplete and not allow_incomplete:
        raise ValueError(f"存在缺少波段的影像组（示例: {', '.join(incomplete[:3])}）")
    usable_groups = [group for group in groups if group.complete]
    if not usable_groups:
        raise ValueError(f"没有完整的多光谱影像组: {flight_dir}")
    output_dir = output_root / flight_dir.name
    if (output_dir / "images").exists():
        raise ValueError(f"输出目录已有 images，请使用新的工作目录: {output_dir}")
    mode = _stage_flight(flight_dir, output_dir, usable_groups)
    representative = _validate_tiff(flight_dir / next(iter(usable_groups[0].bands.values())))
    manifest = {
        "format": "crop-twin-m3m-odm-manifest-1",
        "source_directory": str(flight_dir),
        "image_count": len(usable_groups),
        "discovered_group_count": len(groups),
        "excluded_incomplete_groups": incomplete,
        "band_order": ["visible", *BANDS],
        "staging_mode": mode,
        "tiff_metadata": representative,
        "has_georeferenced_tiff": representative["crs"] is not None,
        "groups": [asdict(group) for group in usable_groups],
        "warnings": [
            "原始单波段 TIFF 没有 CRS/仿射变换，不能直接按 TIFF bounds 显示。",
            "ODM 必须同时读取 D.JPG 和四个 MS_TIF，通过空三结果生成正射影像。",
            "未发现校准板影像时，不应把输出数值宣称为经过现场反射率标定。",
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    command = (
        "docker run --rm -it "
        f'-v "{output_dir.resolve()}:/datasets/code" '
        "opendronemap/odm:3.5.3 "
        "--project-path /datasets "
        "--radiometric-calibration camera "
        "--cog --build-overviews --skip-3dmodel"
    )
    (output_dir / "run-odm.ps1").write_text(command + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="DJI 飞行目录或包含多个飞行目录的父目录")
    parser.add_argument("--output", type=Path, required=True, help="ODM 工作目录，不覆盖原始资料")
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="跳过缺少任一光谱 TIF 的组，并在 manifest 中记录，不把它们送入 ODM",
    )
    args = parser.parse_args()
    input_path = args.input.resolve()
    flights = (
        [input_path]
        if any(input_path.glob("*_D.JPG"))
        else [p for p in input_path.iterdir() if p.is_dir()]
    )
    if not flights:
        parser.error("找不到飞行目录或 *_D.JPG")
    args.output.mkdir(parents=True, exist_ok=True)
    for flight in sorted(flights):
        manifest = prepare_flight(
            flight, args.output.resolve(), allow_incomplete=args.allow_incomplete
        )
        print(
            json.dumps(
                {"flight": flight.name, "images": manifest["image_count"]}, ensure_ascii=False
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

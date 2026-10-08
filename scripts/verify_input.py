"""Verify a downloaded JSON input checksum; do not treat this as model validation."""

import argparse
import json
import re
import secrets
from pathlib import Path

from crop_engine.inputs import content_hash


def verify_input(path: Path) -> None:
    """Read at most 2 MiB, reject altered/non-finite payloads and expose no data in errors."""
    if path.stat().st_size > 2097152:
        raise ValueError("输入快照文件最多 2 MiB")
    with path.open(encoding="utf-8-sig") as stream:
        document = json.load(stream)
    if not isinstance(document, dict) or not isinstance(document.get("payload"), dict):
        raise ValueError("输入快照格式不正确")
    expected = document.get("content_hash")
    if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise ValueError("输入快照缺少有效校验和")
    if not secrets.compare_digest(content_hash(document["payload"]), expected):
        raise ValueError("校验和不一致，文件内容可能已改变")


def main() -> None:
    """Verify one explicit local file without writing it or printing its contents."""
    parser = argparse.ArgumentParser(description="核验输入快照内容，不验证作物模型精度")
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    try:
        verify_input(arguments.path)
    except (OSError, UnicodeError, ValueError):
        raise SystemExit("输入快照核验失败，请核对文件格式、大小和校验和") from None
    print("PASS：输入内容校验和一致；这不代表模型已运行或农艺验证通过。")


if __name__ == "__main__":
    main()

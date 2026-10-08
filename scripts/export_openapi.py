"""Export the implemented API contract, or verify that committed exports are current."""

import argparse
import json
from pathlib import Path

import yaml
from crop_twin.main import create_app

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Write deterministic API exports; --check fails on stale or missing files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    schema = create_app().openapi()
    exports = {
        "openapi.json": json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        "openapi.yaml": yaml.safe_dump(schema, allow_unicode=True, sort_keys=False),
    }
    for filename, content in exports.items():
        path = ROOT / "contracts" / filename
        if arguments.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise SystemExit(f"Stale contract: {path}. Run scripts/export_openapi.py.")
        else:
            path.write_text(content, encoding="utf-8", newline="\n")
    print("OpenAPI exports are current." if arguments.check else "OpenAPI exports written.")


if __name__ == "__main__":
    main()

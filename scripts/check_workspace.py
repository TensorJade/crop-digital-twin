"""Check key scaffold boundaries and reject accidental fake API contracts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    ".gitignore",
    ".env.example",
    "uv.lock",
    "frontend/package-lock.json",
    "backend/src/crop_twin/main.py",
    "packages/crop_engine/pyproject.toml",
    "contracts/openapi.json",
    "docs/progress.md",
    "docs/dev-log/README.md",
    "docs/diagrams/architecture.svg",
    "docs/diagrams/dfd_level1.svg",
    "infra/compose/compose.dev.yaml",
    "scripts/bootstrap.ps1",
]


def main() -> None:
    """Validate scaffold files and the implemented route inventory."""
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        raise SystemExit(f"Missing files: {', '.join(missing)}")
    schema = json.loads((ROOT / "contracts/openapi.json").read_text(encoding="utf-8"))
    if set(schema["paths"]) != {"/api/v1/health"}:
        raise SystemExit("Review route inventory and update requirements before expanding API.")
    print(f"Workspace structure checked ({len(REQUIRED)} required files).")


if __name__ == "__main__":
    main()

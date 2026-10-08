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
    "scripts/init_db.py",
    "backend/migrations/versions/0001_farm_records.py",
    "docs/modules/farm-management.md",
    "frontend/src/features/farm/ManagementPanel.vue",
    "backend/migrations/versions/0002_identity.py",
    "frontend/src/features/identity/LoginPage.vue",
    "docs/modules/identity.md",
    "scripts/create_admin.py",
]


def main() -> None:
    """Validate scaffold files and the implemented route inventory."""
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        raise SystemExit(f"Missing files: {', '.join(missing)}")
    schema = json.loads((ROOT / "contracts/openapi.json").read_text(encoding="utf-8"))
    required_routes = {
        "/api/v1/health",
        "/api/v1/plots",
        "/api/v1/seasons",
        "/api/v1/management-events",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/users",
        "/api/v1/audit-events",
    }
    if not required_routes <= schema["paths"].keys():
        raise SystemExit("An implemented M1 route is missing.")
    operation_ids: list[str] = []
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            if method not in {"get", "post"}:
                raise SystemExit(f"Undocumented HTTP method policy change: {method} {path}")
            operation_ids.append(operation["operationId"])
    if len(operation_ids) != len(set(operation_ids)):
        raise SystemExit("API operation identifiers must be unique.")
    print(f"Workspace structure checked ({len(REQUIRED)} required files).")


if __name__ == "__main__":
    main()

"""Verify actionable database failures and the boundary of unauthenticated deployment."""

from pathlib import Path

import pytest
from crop_twin.core.settings import Settings
from crop_twin.main import create_app
from fastapi.testclient import TestClient
from pydantic import SecretStr


def test_uninitialized_database_returns_safe_error_without_claiming_readiness(
    tmp_path: Path,
) -> None:
    database = tmp_path / "not_migrated.db"
    settings = Settings(
        environment="test", database_url=SecretStr(f"sqlite:///{database.as_posix()}")
    )
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "nobody",
                "password": "never-return-this-password",
            },
        )
        assert client.get("/api/v1/health").status_code == 200
    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "STORAGE_UNAVAILABLE",
            "message": "数据存储暂不可用，请检查数据库初始化或连接",
        }
    }
    assert "SELECT" not in response.text
    assert str(database) not in response.text
    assert "never-return-this-password" not in response.text


def test_production_awaits_the_release_gate() -> None:
    with pytest.raises(RuntimeError, match="authorization"):
        create_app(Settings(environment="production"))

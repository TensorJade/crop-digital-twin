"""Verify the public health contract and avoid false dependency-readiness claims."""

from crop_twin.main import create_app
from fastapi.testclient import TestClient


def test_health_reports_process_liveness() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "crop-twin-api",
        "version": "0.2.0",
        "scope": "process",
    }


def test_openapi_exposes_only_implemented_routes() -> None:
    schema = create_app().openapi()
    assert set(schema["paths"]) == {
        "/api/v1/health",
        "/api/v1/plots",
        "/api/v1/plots/{plot_id}",
        "/api/v1/seasons",
        "/api/v1/seasons/{season_id}/close",
        "/api/v1/management-events",
        "/api/v1/management-events/{event_id}/corrections",
    }
    assert schema["paths"]["/api/v1/health"]["get"]["operationId"] == "getApiHealth"

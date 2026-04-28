from api_gateway.main.app import create_app
from fastapi.testclient import TestClient


def test_api_gateway_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "api-gateway", "status": "ok"}


def test_api_gateway_version_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/version")

    assert response.status_code == 200
    assert response.json() == {"service": "api-gateway", "version": "0.1.0"}

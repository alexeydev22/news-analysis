import logging

from economic_news_framework.apps import create_service_app
from economic_news_framework.health import build_health_response
from economic_news_framework.logging import configure_logging
from economic_news_framework.settings import BaseServiceSettings
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_base_service_settings_reads_defaults() -> None:
    settings = BaseServiceSettings(service_name="api-gateway")

    assert settings.service_name == "api-gateway"
    assert settings.environment == "local"
    assert settings.log_level == "INFO"


def test_configure_logging_sets_root_level() -> None:
    configure_logging("WARNING")

    assert logging.getLogger().level == logging.WARNING


def test_build_health_response_returns_contract_model() -> None:
    response = build_health_response("api-gateway")

    assert response.model_dump() == {"service": "api-gateway", "status": "ok"}


def test_create_service_app_registers_health_endpoint() -> None:
    app = create_service_app(service_name="api-gateway")

    assert isinstance(app, FastAPI)

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "api-gateway", "status": "ok"}

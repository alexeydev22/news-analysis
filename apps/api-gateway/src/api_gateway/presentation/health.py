from economic_news_contracts.health import HealthResponse


def describe_health() -> HealthResponse:
    return HealthResponse(service="api-gateway")

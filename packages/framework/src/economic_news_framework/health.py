from economic_news_contracts.health import HealthResponse


def build_health_response(service_name: str) -> HealthResponse:
    return HealthResponse(service=service_name)

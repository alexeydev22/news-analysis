FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv==0.11.8

COPY pyproject.toml uv.lock ./
COPY packages/framework ./packages/framework
COPY packages/contracts ./packages/contracts
COPY apps/api-gateway ./apps/api-gateway

RUN uv sync --frozen --package economic-news-api-gateway --no-dev

CMD [".venv/bin/granian", "api_gateway.main.app:app", "--interface", "asgi", "--host", "0.0.0.0", "--port", "8000"]

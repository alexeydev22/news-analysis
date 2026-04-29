FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv==0.11.8

COPY pyproject.toml uv.lock ./
COPY packages/framework ./packages/framework
COPY packages/contracts ./packages/contracts
COPY apps/analysis-service ./apps/analysis-service

RUN uv sync --frozen --package economic-news-analysis-service --no-dev

CMD [".venv/bin/granian", "analysis_service.main.app:app", "--interface", "asgi", "--host", "0.0.0.0", "--port", "8000"]

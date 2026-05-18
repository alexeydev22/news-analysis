# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv==0.11.8

COPY pyproject.toml uv.lock ./
COPY packages/framework/pyproject.toml ./packages/framework/pyproject.toml
COPY packages/contracts/pyproject.toml ./packages/contracts/pyproject.toml
COPY apps/dialog-service/pyproject.toml ./apps/dialog-service/pyproject.toml

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package economic-news-dialog-service --no-dev --no-install-workspace

COPY packages/framework ./packages/framework
COPY packages/contracts ./packages/contracts
COPY apps/dialog-service ./apps/dialog-service

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package economic-news-dialog-service --no-dev

CMD [".venv/bin/granian", "dialog_service.main.app:app", "--interface", "asgi", "--host", "0.0.0.0", "--port", "8000"]

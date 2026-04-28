FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY packages/framework ./packages/framework
COPY packages/contracts ./packages/contracts
COPY apps/api-gateway ./apps/api-gateway

RUN uv pip install --system --no-cache \
    ./packages/framework \
    ./packages/contracts \
    ./apps/api-gateway

CMD ["granian", "api_gateway.main.app:app", "--interface", "asgi", "--host", "0.0.0.0", "--port", "8000"]

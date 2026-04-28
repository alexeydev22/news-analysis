set shell := ["zsh", "-cu"]

fmt:
    uv run ruff format apps packages

lint:
    uv run ruff check apps packages

typecheck:
    uv run ty check apps packages

test:
    uv run pytest packages apps -v

compose-up:
    docker compose -f deploy/compose.yaml up --build

compose-down:
    docker compose -f deploy/compose.yaml down

api-dev:
    granian api_gateway.main.app:app --interface asgi --host 0.0.0.0 --port 8000

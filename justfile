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

demo-up:
    docker compose -f deploy/compose.yaml up --build

demo-up-trained:
    ANALYSIS_USE_STATIC_CLASSIFIER=false docker compose -f deploy/compose.yaml up --build

demo-smoke:
    uv run python tools/demo_smoke.py

demo-smoke-no-frontend:
    uv run python tools/demo_smoke.py --skip-frontend

demo-down:
    docker compose -f deploy/compose.yaml down

api-dev:
    uv run --package economic-news-api-gateway granian api_gateway.main.app:app --interface asgi --host 0.0.0.0 --port 8000

analysis-dev:
    ANALYSIS_USE_STATIC_CLASSIFIER=true uv run --package economic-news-analysis-service granian analysis_service.main.app:app --interface asgi --host 0.0.0.0 --port 8001

dialog:
    uv run --package economic-news-dialog-service granian dialog_service.main.app:app --interface asgi --host 0.0.0.0 --port 8003

news-worker:
    uv run --package economic-news-news-service taskiq worker news_service.workers.broker:broker news_service.workers.tasks --workers 1

web-dev:
    npm --prefix frontend/web run dev -- --host 0.0.0.0 --port 5173

web-test:
    npm --prefix frontend/web test -- --run

web-build:
    npm --prefix frontend/web run build

prepare-dataset input +args='':
    uv run python tools/prepare_dataset.py {{input}} {{args}}

train-baseline:
    uv run --project research python -m economic_news_research.cli train-baseline --dataset data/raw/news_impact.csv --output-dir artifacts/models/baseline

train-embedding:
    uv run --project research python -m economic_news_research.cli train-embedding --dataset data/raw/news_impact.csv --output-dir artifacts/models/embedding

train-transformer:
    uv run --project research python -m economic_news_research.cli train-transformer --dataset data/raw/news_impact.csv --output-dir artifacts/models/transformer

compare-models:
    uv run --project research python -m economic_news_research.cli compare-models

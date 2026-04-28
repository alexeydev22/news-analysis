# Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать базовую структуру monorepo, GitHub-репозиторий, веточную модель, общий framework/contracts пакет и минимальный FastAPI + Granian + Dishka сервис как шаблон для остальных микросервисов.

**Architecture:** Foundation задает технический каркас без бизнес-логики: shared framework, shared contracts, один пример сервиса `api-gateway`, Docker Compose, Justfile и правила разработки. Каждый будущий сервис будет повторять слои `domain`, `application`, `infrastructure`, `presentation`, `main`, `workers`, а интерфейсы будут описываться через `typing.Protocol`.

**Tech Stack:** Python, FastAPI, Granian, Dishka, Pydantic Settings, structlog, pytest, ruff, ty, Docker Compose, Justfile, GitHub, Git branches `master`, `dev`, `feature/*`.

---

## Repository and Branching Rules

- GitHub repository URL: `https://github.com/alexeydev22/news-analysis.git`.
- Visibility: public, because coursework guidelines require a public repository link.
- Main stable branch: `master`.
- Integration branch: `dev`.
- Work branches: `feature/foundation`, `feature/ml-research`, `feature/core-services`, `feature/api-ui`, `feature/coursework-presentation`.
- Commit messages: Russian text with conventional prefixes:
  - `feat: добавить базовую структуру монорепозитория`
  - `fix: исправить настройку контейнера зависимостей`
  - `refactor: упростить создание FastAPI приложения`
  - `test: добавить проверки healthcheck`
  - `docs: описать запуск проекта`
  - `chore: настроить docker compose`

## File Structure

Create this foundation structure:

```text
apps/
  api-gateway/
    pyproject.toml
    src/api_gateway/
      domain/
        __init__.py
      application/
        __init__.py
        ports.py
      infrastructure/
        __init__.py
      presentation/
        __init__.py
        health.py
        router.py
      main/
        __init__.py
        app.py
        container.py
        settings.py
      workers/
        __init__.py
    tests/
      test_health.py
packages/
  framework/
    pyproject.toml
    src/economic_news_framework/
      __init__.py
      apps.py
      logging.py
      settings.py
      health.py
      errors.py
  contracts/
    pyproject.toml
    src/economic_news_contracts/
      __init__.py
      analysis.py
      events.py
      health.py
frontend/
  web/
research/
  notebooks/
  scripts/
  reports/
data/
  raw/
  processed/
  external/
artifacts/
  models/
  indexes/
  mlflow/
docs/
  coursework/
  presentation/
deploy/
  docker/
  compose.yaml
.dockerignore
.env.example
.gitignore
justfile
pyproject.toml
README.md
```

Root `pyproject.toml` owns repo-level tooling. Each package/service has its own `pyproject.toml` for future independent packaging, but local development can run from the monorepo with editable installs.

---

### Task 1: Initialize Git and Connect Existing GitHub Repository

**Files:**
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Write `.gitignore`**

Create `.gitignore` with:

```gitignore
.DS_Store
.env
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.mypy_cache/
.ty/
.coverage
htmlcov/

data/raw/*
data/processed/*
data/external/*
!data/raw/.gitkeep
!data/processed/.gitkeep
!data/external/.gitkeep

artifacts/models/*
artifacts/indexes/*
artifacts/mlflow/*
!artifacts/models/.gitkeep
!artifacts/indexes/.gitkeep
!artifacts/mlflow/.gitkeep

.superpowers/
node_modules/
dist/
build/
```

- [ ] **Step 2: Write initial `README.md`**

Create `README.md` with:

```markdown
# Economic News Dialog System

Локальная микросервисная диалоговая система для анализа экономических новостей.

## Тема курсовой работы

Разработка автоматической диалоговой системы на основе языковой модели для анализа экономических новостей.

## Архитектура

Проект строится как monorepo:

- `apps/` — backend-микросервисы;
- `packages/framework` — общий технический foundation;
- `packages/contracts` — общие DTO и event schemas;
- `frontend/web` — React UI;
- `research/` — notebooks, training scripts, reports;
- `docs/` — пояснительная записка и презентация;
- `deploy/` — Docker Compose и Dockerfiles.

## Ветки

- `master` — стабильная основная ветка;
- `dev` — ветка разработки и интеграционного тестирования;
- `feature/*` — ветки отдельных этапов.

## Commit style

Коммиты пишутся на русском языке с conventional prefix:

- `feat: добавить ...`
- `fix: исправить ...`
- `refactor: упростить ...`
- `test: добавить ...`
- `docs: описать ...`
- `chore: настроить ...`
```

- [ ] **Step 3: Initialize git repository**

Run:

```bash
git init
git branch -M master
git add .gitignore README.md docs/superpowers/specs/2026-04-28-economic-news-dialog-system-design.md docs/superpowers/plans/2026-04-28-foundation-plan.md
git commit -m "docs: добавить спецификацию и план foundation"
```

Expected: git creates the first commit on `master`.

- [ ] **Step 4: Connect existing GitHub repository**

Run:

```bash
git remote add origin https://github.com/alexeydev22/news-analysis.git
git push -u origin master
```

Expected: existing public GitHub repo is connected and `master` is pushed to `origin/master`.

- [ ] **Step 5: Create `dev` branch**

Run:

```bash
git checkout -b dev
git push -u origin dev
```

Expected: local and remote `dev` branches exist.

- [ ] **Step 6: Create foundation feature branch**

Run:

```bash
git checkout -b feature/foundation
```

Expected: all remaining foundation work happens on `feature/foundation`.

---

### Task 2: Create Monorepo Directories and Keep Files

**Files:**
- Create: `apps/api-gateway/src/api_gateway/domain/__init__.py`
- Create: `apps/api-gateway/src/api_gateway/application/__init__.py`
- Create: `apps/api-gateway/src/api_gateway/infrastructure/__init__.py`
- Create: `apps/api-gateway/src/api_gateway/presentation/__init__.py`
- Create: `apps/api-gateway/src/api_gateway/main/__init__.py`
- Create: `apps/api-gateway/src/api_gateway/workers/__init__.py`
- Create: `apps/api-gateway/tests/__init__.py`
- Create: `packages/framework/src/economic_news_framework/__init__.py`
- Create: `packages/contracts/src/economic_news_contracts/__init__.py`
- Create: `data/raw/.gitkeep`
- Create: `data/processed/.gitkeep`
- Create: `data/external/.gitkeep`
- Create: `artifacts/models/.gitkeep`
- Create: `artifacts/indexes/.gitkeep`
- Create: `artifacts/mlflow/.gitkeep`

- [ ] **Step 1: Create directories**

Run:

```bash
mkdir -p apps/api-gateway/src/api_gateway/{domain,application,infrastructure,presentation,main,workers}
mkdir -p apps/api-gateway/tests
mkdir -p packages/framework/src/economic_news_framework
mkdir -p packages/contracts/src/economic_news_contracts
mkdir -p frontend/web research/notebooks research/scripts research/reports
mkdir -p data/raw data/processed data/external
mkdir -p artifacts/models artifacts/indexes artifacts/mlflow
mkdir -p docs/coursework docs/presentation deploy/docker
```

Expected: all directories exist.

- [ ] **Step 2: Add package marker files**

Run:

```bash
touch apps/api-gateway/src/api_gateway/domain/__init__.py
touch apps/api-gateway/src/api_gateway/application/__init__.py
touch apps/api-gateway/src/api_gateway/infrastructure/__init__.py
touch apps/api-gateway/src/api_gateway/presentation/__init__.py
touch apps/api-gateway/src/api_gateway/main/__init__.py
touch apps/api-gateway/src/api_gateway/workers/__init__.py
touch apps/api-gateway/tests/__init__.py
touch packages/framework/src/economic_news_framework/__init__.py
touch packages/contracts/src/economic_news_contracts/__init__.py
touch data/raw/.gitkeep data/processed/.gitkeep data/external/.gitkeep
touch artifacts/models/.gitkeep artifacts/indexes/.gitkeep artifacts/mlflow/.gitkeep
```

Expected: package markers and `.gitkeep` files exist.

- [ ] **Step 3: Commit directory structure**

Run:

```bash
git add apps packages frontend research data artifacts docs/coursework docs/presentation deploy
git commit -m "feat: добавить структуру монорепозитория"
```

Expected: commit succeeds on `feature/foundation`.

---

### Task 3: Configure Python Tooling

**Files:**
- Create: `pyproject.toml`
- Create: `packages/framework/pyproject.toml`
- Create: `packages/contracts/pyproject.toml`
- Create: `apps/api-gateway/pyproject.toml`

- [ ] **Step 1: Write root `pyproject.toml`**

Create `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py312"
line-length = 100
src = ["apps", "packages", "research/scripts"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "ASYNC"]
ignore = []

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.pytest.ini_options]
testpaths = ["apps", "packages"]
pythonpath = [
  "packages/framework/src",
  "packages/contracts/src",
  "apps/api-gateway/src",
]
asyncio_mode = "auto"

[tool.ty.src]
include = ["apps", "packages"]
```

- [ ] **Step 2: Write `packages/framework/pyproject.toml`**

Create `packages/framework/pyproject.toml`:

```toml
[project]
name = "economic-news-framework"
version = "0.1.0"
description = "Shared technical framework for the economic news dialog system"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "dishka>=1.4",
  "pydantic-settings>=2.6",
  "structlog>=24.4",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 3: Write `packages/contracts/pyproject.toml`**

Create `packages/contracts/pyproject.toml`:

```toml
[project]
name = "economic-news-contracts"
version = "0.1.0"
description = "Shared DTO and event contracts for the economic news dialog system"
requires-python = ">=3.12"
dependencies = [
  "pydantic>=2.10",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 4: Write `apps/api-gateway/pyproject.toml`**

Create `apps/api-gateway/pyproject.toml`:

```toml
[project]
name = "economic-news-api-gateway"
version = "0.1.0"
description = "API gateway for the economic news dialog system"
requires-python = ">=3.12"
dependencies = [
  "economic-news-framework",
  "economic-news-contracts",
  "fastapi>=0.115",
  "granian>=1.7",
  "dishka>=1.4",
  "pydantic-settings>=2.6",
  "structlog>=24.4",
]

[project.optional-dependencies]
test = [
  "httpx>=0.28",
  "pytest>=8.3",
  "pytest-asyncio>=0.24",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv.sources]
economic-news-framework = { path = "../../packages/framework", editable = true }
economic-news-contracts = { path = "../../packages/contracts", editable = true }
```

- [ ] **Step 5: Run formatting and checks**

Run:

```bash
uv run ruff format pyproject.toml packages/framework/pyproject.toml packages/contracts/pyproject.toml apps/api-gateway/pyproject.toml
uv run ruff check pyproject.toml packages/framework/pyproject.toml packages/contracts/pyproject.toml apps/api-gateway/pyproject.toml
```

Expected: both commands pass.

- [ ] **Step 6: Commit tooling config**

Run:

```bash
git add pyproject.toml packages/framework/pyproject.toml packages/contracts/pyproject.toml apps/api-gateway/pyproject.toml
git commit -m "chore: настроить python tooling"
```

Expected: commit succeeds.

---

### Task 4: Implement Shared Contracts

**Files:**
- Create: `packages/contracts/src/economic_news_contracts/analysis.py`
- Create: `packages/contracts/src/economic_news_contracts/events.py`
- Create: `packages/contracts/src/economic_news_contracts/health.py`
- Create: `packages/contracts/tests/test_contracts.py`

- [ ] **Step 1: Write failing tests**

Create `packages/contracts/tests/test_contracts.py`:

```python
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel
from economic_news_contracts.events import EventEnvelope
from economic_news_contracts.health import HealthResponse


def test_impact_label_values_are_stable() -> None:
    assert ImpactLabel.POSITIVE == "positive"
    assert ImpactLabel.NEUTRAL == "neutral"
    assert ImpactLabel.NEGATIVE == "negative"


def test_analysis_model_names_are_stable() -> None:
    assert AnalysisModelName.TFIDF_LOGREG == "tfidf-logreg"
    assert AnalysisModelName.RUBERT_TINY2_CLASSIFIER == "rubert-tiny2-classifier"
    assert AnalysisModelName.RUBERT_TINY2_FINETUNED == "rubert-tiny2-finetuned"


def test_event_envelope_contains_type_and_payload() -> None:
    event = EventEnvelope(event_type="analysis.completed", payload={"article_id": "a-1"})

    assert event.event_type == "analysis.completed"
    assert event.payload == {"article_id": "a-1"}


def test_health_response_defaults_to_ok() -> None:
    response = HealthResponse(service="api-gateway")

    assert response.status == "ok"
    assert response.service == "api-gateway"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest packages/contracts/tests/test_contracts.py -v
```

Expected: FAIL because contract modules are not implemented.

- [ ] **Step 3: Implement analysis contracts**

Create `packages/contracts/src/economic_news_contracts/analysis.py`:

```python
from enum import StrEnum


class ImpactLabel(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class AnalysisModelName(StrEnum):
    TFIDF_LOGREG = "tfidf-logreg"
    RUBERT_TINY2_CLASSIFIER = "rubert-tiny2-classifier"
    RUBERT_TINY2_FINETUNED = "rubert-tiny2-finetuned"
```

- [ ] **Step 4: Implement event contracts**

Create `packages/contracts/src/economic_news_contracts/events.py`:

```python
from typing import Any

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    event_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 5: Implement health contracts**

Create `packages/contracts/src/economic_news_contracts/health.py`:

```python
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    service: str = Field(min_length=1)
    status: str = "ok"
```

- [ ] **Step 6: Run tests**

Run:

```bash
uv run pytest packages/contracts/tests/test_contracts.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit contracts**

Run:

```bash
git add packages/contracts
git commit -m "feat: добавить общие контракты сервисов"
```

Expected: commit succeeds.

---

### Task 5: Implement Shared Framework

**Files:**
- Create: `packages/framework/src/economic_news_framework/settings.py`
- Create: `packages/framework/src/economic_news_framework/logging.py`
- Create: `packages/framework/src/economic_news_framework/health.py`
- Create: `packages/framework/src/economic_news_framework/errors.py`
- Create: `packages/framework/src/economic_news_framework/apps.py`
- Create: `packages/framework/tests/test_framework.py`

- [ ] **Step 1: Write failing framework tests**

Create `packages/framework/tests/test_framework.py`:

```python
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from economic_news_framework.apps import create_service_app
from economic_news_framework.health import build_health_response
from economic_news_framework.logging import configure_logging
from economic_news_framework.settings import BaseServiceSettings


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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest packages/framework/tests/test_framework.py -v
```

Expected: FAIL because framework modules are not implemented.

- [ ] **Step 3: Implement settings**

Create `packages/framework/src/economic_news_framework/settings.py`:

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    service_name: str
    environment: str = "local"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
```

- [ ] **Step 4: Implement logging setup**

Create `packages/framework/src/economic_news_framework/logging.py`:

```python
import logging
import sys

import structlog


def configure_logging(level: str) -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
        force=True,
    )
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

- [ ] **Step 5: Implement health helper**

Create `packages/framework/src/economic_news_framework/health.py`:

```python
from economic_news_contracts.health import HealthResponse


def build_health_response(service_name: str) -> HealthResponse:
    return HealthResponse(service=service_name)
```

- [ ] **Step 6: Implement error model**

Create `packages/framework/src/economic_news_framework/errors.py`:

```python
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
```

- [ ] **Step 7: Implement FastAPI app factory**

Create `packages/framework/src/economic_news_framework/apps.py`:

```python
from collections.abc import Iterable

from fastapi import APIRouter, FastAPI

from economic_news_framework.health import build_health_response
from economic_news_framework.logging import configure_logging


def create_service_app(
    *,
    service_name: str,
    routers: Iterable[APIRouter] = (),
    log_level: str = "INFO",
) -> FastAPI:
    configure_logging(log_level)
    app = FastAPI(title=service_name)

    @app.get("/health")
    async def health():
        return build_health_response(service_name)

    for router in routers:
        app.include_router(router)

    return app
```

- [ ] **Step 8: Run framework tests**

Run:

```bash
uv run pytest packages/framework/tests/test_framework.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit framework**

Run:

```bash
git add packages/framework
git commit -m "feat: добавить общий framework сервисов"
```

Expected: commit succeeds.

---

### Task 6: Implement Minimal API Gateway

**Files:**
- Create: `apps/api-gateway/src/api_gateway/application/ports.py`
- Create: `apps/api-gateway/src/api_gateway/presentation/health.py`
- Create: `apps/api-gateway/src/api_gateway/presentation/router.py`
- Create: `apps/api-gateway/src/api_gateway/main/settings.py`
- Create: `apps/api-gateway/src/api_gateway/main/container.py`
- Create: `apps/api-gateway/src/api_gateway/main/app.py`
- Create: `apps/api-gateway/tests/test_health.py`

- [ ] **Step 1: Write failing API gateway tests**

Create `apps/api-gateway/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from api_gateway.main.app import create_app


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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_health.py -v
```

Expected: FAIL because `api_gateway.main.app` is not implemented.

- [ ] **Step 3: Define an application port**

Create `apps/api-gateway/src/api_gateway/application/ports.py`:

```python
from typing import Protocol


class VersionProvider(Protocol):
    def get_version(self) -> str:
        """Return current service version."""
```

- [ ] **Step 4: Implement settings**

Create `apps/api-gateway/src/api_gateway/main/settings.py`:

```python
from economic_news_framework.settings import BaseServiceSettings


class ApiGatewaySettings(BaseServiceSettings):
    service_name: str = "api-gateway"
    version: str = "0.1.0"
```

- [ ] **Step 5: Implement DI container**

Create `apps/api-gateway/src/api_gateway/main/container.py`:

```python
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider

from api_gateway.main.settings import ApiGatewaySettings


class ApiGatewayProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> ApiGatewaySettings:
        return ApiGatewaySettings()


def create_container():
    return make_async_container(ApiGatewayProvider(), FastapiProvider())
```

- [ ] **Step 6: Implement router**

Create `apps/api-gateway/src/api_gateway/presentation/router.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


@router.get("/version")
async def version() -> dict[str, str]:
    return {"service": "api-gateway", "version": "0.1.0"}
```

- [ ] **Step 7: Keep presentation health module explicit**

Create `apps/api-gateway/src/api_gateway/presentation/health.py`:

```python
from economic_news_contracts.health import HealthResponse


def describe_health() -> HealthResponse:
    return HealthResponse(service="api-gateway")
```

- [ ] **Step 8: Implement app factory and Granian target**

Create `apps/api-gateway/src/api_gateway/main/app.py`:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from dishka.integrations.fastapi import setup_dishka

from api_gateway.main.container import create_container
from api_gateway.main.settings import ApiGatewaySettings
from api_gateway.presentation.router import router
from economic_news_framework.apps import create_service_app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.dishka_container.close()


def create_app() -> FastAPI:
    settings = ApiGatewaySettings()
    container = create_container()
    app = create_service_app(
        service_name=settings.service_name,
        routers=(router,),
        log_level=settings.log_level,
    )
    app.router.lifespan_context = lifespan
    setup_dishka(container=container, app=app)
    return app


app = create_app()
```

- [ ] **Step 9: Run API gateway tests**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_health.py -v
```

Expected: PASS.

- [ ] **Step 10: Run all tests**

Run:

```bash
uv run pytest packages apps -v
```

Expected: PASS.

- [ ] **Step 11: Commit API gateway skeleton**

Run:

```bash
git add apps/api-gateway
git commit -m "feat: добавить базовый api gateway"
```

Expected: commit succeeds.

---

### Task 7: Add Docker Compose, Dockerfile, and Justfile

**Files:**
- Create: `deploy/compose.yaml`
- Create: `deploy/docker/api-gateway.Dockerfile`
- Create: `.dockerignore`
- Create: `.env.example`
- Create: `justfile`

- [ ] **Step 1: Write `.dockerignore`**

Create `.dockerignore`:

```dockerignore
.git
.venv
__pycache__
.pytest_cache
.ruff_cache
.superpowers
data/raw
data/processed
data/external
artifacts
node_modules
dist
build
```

- [ ] **Step 2: Write `.env.example`**

Create `.env.example`:

```dotenv
ENVIRONMENT=local
LOG_LEVEL=INFO
POSTGRES_DB=economic_news
POSTGRES_USER=economic_news
POSTGRES_PASSWORD=economic_news
REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333
MLFLOW_TRACKING_URI=http://mlflow:5000
```

- [ ] **Step 3: Write API gateway Dockerfile**

Create `deploy/docker/api-gateway.Dockerfile`:

```dockerfile
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
```

- [ ] **Step 4: Write Docker Compose**

Create `deploy/compose.yaml`:

```yaml
services:
  api-gateway:
    build:
      context: ..
      dockerfile: deploy/docker/api-gateway.Dockerfile
    env_file:
      - ../.env.example
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - qdrant

  postgres:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: economic_news
      POSTGRES_USER: economic_news
      POSTGRES_PASSWORD: economic_news
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.19.0
    command: mlflow server --host 0.0.0.0 --port 5000
    ports:
      - "5000:5000"
    volumes:
      - mlflow_data:/mlflow

volumes:
  postgres_data:
  qdrant_data:
  mlflow_data:
```

- [ ] **Step 5: Write `justfile`**

Create `justfile`:

```just
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
```

- [ ] **Step 6: Run local checks**

Run:

```bash
uv run ruff format apps packages
uv run ruff check apps packages
uv run pytest packages apps -v
```

Expected: all commands pass.

- [ ] **Step 7: Build Docker Compose**

Run:

```bash
docker compose -f deploy/compose.yaml build api-gateway
```

Expected: `api-gateway` image builds successfully.

- [ ] **Step 8: Commit deployment foundation**

Run:

```bash
git add deploy .dockerignore .env.example justfile
git commit -m "chore: настроить docker compose и justfile"
```

Expected: commit succeeds.

---

### Task 8: Verify Foundation and Push Feature Branch

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README with run commands**

Append to `README.md`:

```markdown
## Локальный запуск foundation

```bash
just test
just compose-up
```

API Gateway healthcheck:

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:

```json
{"service":"api-gateway","status":"ok"}
```
```

- [ ] **Step 2: Run final checks**

Run:

```bash
uv run ruff format apps packages
uv run ruff check apps packages
uv run ty check apps packages
uv run pytest packages apps -v
docker compose -f deploy/compose.yaml build api-gateway
```

Expected: all commands pass.

- [ ] **Step 3: Commit README update**

Run:

```bash
git add README.md
git commit -m "docs: описать запуск foundation"
```

Expected: commit succeeds.

- [ ] **Step 4: Push feature branch**

Run:

```bash
git push -u origin feature/foundation
```

Expected: `feature/foundation` exists on GitHub.

- [ ] **Step 5: Open pull request to `dev`**

Run:

```bash
gh pr create --base dev --head feature/foundation --title "feat: добавить foundation проекта" --body "Добавлена базовая структура monorepo, общий framework/contracts, API Gateway skeleton, Docker Compose и Justfile."
```

Expected: GitHub PR from `feature/foundation` to `dev` is created.

---

## Self-Review Checklist

- Spec coverage:
  - Monorepo structure: Task 2.
  - Existing GitHub repo and branch model: Task 1.
  - Shared framework/contracts: Tasks 4 and 5.
  - Layered service structure with `main/`: Task 2 and Task 6.
  - FastAPI + Granian + Dishka: Task 6 and Task 7.
  - Docker Compose, slim Dockerfile, Justfile: Task 7.
  - Russian conventional commits: Task 1 and all commit steps.
- Placeholder scan: no unfinished markers, deferred implementation notes, or unspecified tests.
- Type consistency: `ImpactLabel`, `AnalysisModelName`, `HealthResponse`, `BaseServiceSettings`, and `create_service_app` are defined before use.

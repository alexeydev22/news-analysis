# Analysis Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first core backend microservice, `analysis-service`, exposing economic news impact classification through a small DDD-oriented FastAPI service.

**Architecture:** Start with shared contracts and workspace wiring, then build `analysis-service` from domain inward to infrastructure and HTTP presentation. Keep this slice focused on synchronous impact classification and joblib artifact loading; do not add Redis, Taskiq, FastStream, Qdrant, PostgreSQL, SSE, UI, or LLM calls.

**Tech Stack:** Python 3.12+, FastAPI, Granian, Dishka, Pydantic v2, pydantic-settings, joblib, pytest, ruff, ty, uv workspace.

---

## Files Overview

Create:

```text
apps/analysis-service/pyproject.toml
apps/analysis-service/src/analysis_service/__init__.py
apps/analysis-service/src/analysis_service/domain/__init__.py
apps/analysis-service/src/analysis_service/domain/errors.py
apps/analysis-service/src/analysis_service/domain/model.py
apps/analysis-service/src/analysis_service/application/__init__.py
apps/analysis-service/src/analysis_service/application/ports.py
apps/analysis-service/src/analysis_service/application/use_cases.py
apps/analysis-service/src/analysis_service/infrastructure/__init__.py
apps/analysis-service/src/analysis_service/infrastructure/classifiers.py
apps/analysis-service/src/analysis_service/main/__init__.py
apps/analysis-service/src/analysis_service/main/app.py
apps/analysis-service/src/analysis_service/main/container.py
apps/analysis-service/src/analysis_service/main/settings.py
apps/analysis-service/src/analysis_service/presentation/__init__.py
apps/analysis-service/src/analysis_service/presentation/errors.py
apps/analysis-service/src/analysis_service/presentation/router.py
apps/analysis-service/src/analysis_service/workers/__init__.py
apps/analysis-service/tests/__init__.py
apps/analysis-service/tests/test_api.py
apps/analysis-service/tests/test_domain.py
apps/analysis-service/tests/test_infrastructure.py
apps/analysis-service/tests/test_use_cases.py
deploy/docker/analysis-service.Dockerfile
```

Modify:

```text
pyproject.toml
Justfile
deploy/compose.yaml
packages/contracts/src/economic_news_contracts/analysis.py
packages/contracts/tests/test_contracts.py
uv.lock
```

---

### Task 1: Workspace and Shared Contracts

**Files:**

- Modify: `pyproject.toml`
- Modify: `packages/contracts/src/economic_news_contracts/analysis.py`
- Modify: `packages/contracts/tests/test_contracts.py`
- Create: `apps/analysis-service/pyproject.toml`
- Create: `apps/analysis-service/src/analysis_service/__init__.py`
- Create: service package `__init__.py` files
- Modify: `uv.lock`

- [ ] **Step 1: Write failing contract tests**

Update `packages/contracts/tests/test_contracts.py` so model names match real research artifacts and analysis DTOs are covered:

```python
from economic_news_contracts.analysis import (
    AnalysisModelName,
    AnalyzeNewsRequest,
    AnalyzeNewsResponse,
    ImpactLabel,
)
from economic_news_contracts.events import EventEnvelope
from economic_news_contracts.health import HealthResponse


def test_impact_label_values_are_stable() -> None:
    assert ImpactLabel.POSITIVE == "positive"
    assert ImpactLabel.NEUTRAL == "neutral"
    assert ImpactLabel.NEGATIVE == "negative"


def test_analysis_model_names_are_stable() -> None:
    assert AnalysisModelName.TFIDF_LOGREG == "tfidf-logreg"
    assert AnalysisModelName.EMBEDDING_LOGREG == "embedding-logreg"
    assert AnalysisModelName.TINY_TRANSFORMER_CLASSIFIER == "tiny-transformer-classifier"


def test_analyze_news_request_trims_text() -> None:
    request = AnalyzeNewsRequest(
        text="  Central bank keeps rates unchanged.  ",
        analysis_model=AnalysisModelName.TFIDF_LOGREG,
    )

    assert request.text == "Central bank keeps rates unchanged."
    assert request.analysis_model == AnalysisModelName.TFIDF_LOGREG


def test_analyze_news_response_serializes_model_and_impact() -> None:
    response = AnalyzeNewsResponse(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        impact=ImpactLabel.NEUTRAL,
        confidence=None,
        explanation="Model classified the news text as neutral.",
        metadata={},
    )

    assert response.model_dump(mode="json") == {
        "model_name": "tfidf-logreg",
        "impact": "neutral",
        "confidence": None,
        "explanation": "Model classified the news text as neutral.",
        "metadata": {},
    }
```

Keep existing event and health tests below these functions.

- [ ] **Step 2: Run contract tests to verify failure**

Run:

```bash
uv run pytest packages/contracts/tests/test_contracts.py -v
```

Expected: fail because `AnalyzeNewsRequest`, `AnalyzeNewsResponse`, and new enum values do not exist yet.

- [ ] **Step 3: Implement analysis contracts**

Replace `packages/contracts/src/economic_news_contracts/analysis.py` with:

```python
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ImpactLabel(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class AnalysisModelName(StrEnum):
    TFIDF_LOGREG = "tfidf-logreg"
    EMBEDDING_LOGREG = "embedding-logreg"
    TINY_TRANSFORMER_CLASSIFIER = "tiny-transformer-classifier"


class AnalyzeNewsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    analysis_model: AnalysisModelName = AnalysisModelName.TFIDF_LOGREG

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("News text must not be empty")
        return normalized


class AnalyzeNewsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: AnalysisModelName
    impact: ImpactLabel
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    explanation: str
    metadata: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Add analysis-service workspace package**

Create `apps/analysis-service/pyproject.toml`:

```toml
[project]
name = "economic-news-analysis-service"
version = "0.1.0"
description = "Analysis service for economic news impact classification"
requires-python = ">=3.12"
dependencies = [
  "economic-news-framework",
  "economic-news-contracts",
  "fastapi>=0.115",
  "granian>=1.7",
  "dishka>=1.4",
  "joblib>=1.4",
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

[tool.hatch.build.targets.wheel]
packages = ["src/analysis_service"]

[tool.uv.sources]
economic-news-framework = { workspace = true }
economic-news-contracts = { workspace = true }
```

Create empty package files:

```text
apps/analysis-service/src/analysis_service/__init__.py
apps/analysis-service/src/analysis_service/domain/__init__.py
apps/analysis-service/src/analysis_service/application/__init__.py
apps/analysis-service/src/analysis_service/infrastructure/__init__.py
apps/analysis-service/src/analysis_service/main/__init__.py
apps/analysis-service/src/analysis_service/presentation/__init__.py
apps/analysis-service/src/analysis_service/workers/__init__.py
```

- [ ] **Step 5: Wire workspace paths**

Update root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = [
  "packages/framework",
  "packages/contracts",
  "apps/api-gateway",
  "apps/analysis-service",
  "research",
]

[tool.pytest.ini_options]
pythonpath = [
  "packages/framework/src",
  "packages/contracts/src",
  "apps/api-gateway/src",
  "apps/analysis-service/src",
  "research/scripts",
]
```

- [ ] **Step 6: Lock dependencies**

Run:

```bash
uv lock
```

Expected: lock file includes `economic-news-analysis-service`.

- [ ] **Step 7: Verify contracts and formatting**

Run:

```bash
uv run pytest packages/contracts/tests/test_contracts.py -v -W error
uv run ruff check pyproject.toml packages/contracts apps/analysis-service
uv run ty check packages/contracts
```

Expected: all pass.

- [ ] **Step 8: Commit**

Run:

```bash
git add pyproject.toml uv.lock packages/contracts apps/analysis-service
git commit -m "feat: добавить контракты analysis service"
```

---

### Task 2: Domain and Use Case

**Files:**

- Create: `apps/analysis-service/src/analysis_service/domain/errors.py`
- Create: `apps/analysis-service/src/analysis_service/domain/model.py`
- Create: `apps/analysis-service/src/analysis_service/application/ports.py`
- Create: `apps/analysis-service/src/analysis_service/application/use_cases.py`
- Create: `apps/analysis-service/tests/test_domain.py`
- Create: `apps/analysis-service/tests/test_use_cases.py`

- [ ] **Step 1: Write domain tests**

Create `apps/analysis-service/tests/test_domain.py`:

```python
import pytest

from analysis_service.domain.errors import EmptyNewsTextError
from analysis_service.domain.model import ImpactPrediction, NewsText
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel


def test_news_text_trims_value() -> None:
    news_text = NewsText.from_raw("  Markets rise after strong earnings.  ")

    assert news_text.value == "Markets rise after strong earnings."


def test_news_text_rejects_blank_value() -> None:
    with pytest.raises(EmptyNewsTextError):
        NewsText.from_raw("   ")


def test_impact_prediction_builds_default_explanation() -> None:
    prediction = ImpactPrediction(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        impact=ImpactLabel.POSITIVE,
    )

    assert prediction.explanation == "Model classified the news text as positive."
    assert prediction.confidence is None
    assert prediction.metadata == {}
```

- [ ] **Step 2: Write use case tests**

Create `apps/analysis-service/tests/test_use_cases.py`:

```python
import pytest

from analysis_service.application.ports import ImpactClassifier
from analysis_service.application.use_cases import AnalyzeNewsImpact
from analysis_service.domain.errors import ModelUnavailableError
from analysis_service.domain.model import ImpactPrediction, NewsText
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel


class FakeClassifier:
    model_name = AnalysisModelName.TFIDF_LOGREG

    def predict(self, text: NewsText) -> ImpactPrediction:
        assert text.value == "Markets rise"
        return ImpactPrediction(
            model_name=self.model_name,
            impact=ImpactLabel.POSITIVE,
            confidence=0.9,
        )


class FakeRegistry:
    def __init__(self, classifier: ImpactClassifier | None = None) -> None:
        self.classifier = classifier
        self.requested_model: AnalysisModelName | None = None

    def get(self, model_name: AnalysisModelName) -> ImpactClassifier:
        self.requested_model = model_name
        if self.classifier is None:
            raise ModelUnavailableError(model_name)
        return self.classifier


def test_analyze_news_impact_uses_requested_model() -> None:
    registry = FakeRegistry(FakeClassifier())
    use_case = AnalyzeNewsImpact(registry)

    prediction = use_case.execute(
        text=" Markets rise ",
        model_name=AnalysisModelName.TFIDF_LOGREG,
    )

    assert registry.requested_model == AnalysisModelName.TFIDF_LOGREG
    assert prediction.impact == ImpactLabel.POSITIVE
    assert prediction.confidence == 0.9


def test_analyze_news_impact_propagates_unavailable_model() -> None:
    use_case = AnalyzeNewsImpact(FakeRegistry())

    with pytest.raises(ModelUnavailableError):
        use_case.execute(
            text="Markets rise",
            model_name=AnalysisModelName.TFIDF_LOGREG,
        )
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_domain.py apps/analysis-service/tests/test_use_cases.py -v
```

Expected: fail because domain and application modules are missing.

- [ ] **Step 4: Implement domain errors**

Create `apps/analysis-service/src/analysis_service/domain/errors.py`:

```python
from economic_news_contracts.analysis import AnalysisModelName


class AnalysisServiceError(Exception):
    """Base exception for analysis-service."""


class EmptyNewsTextError(AnalysisServiceError):
    def __init__(self) -> None:
        super().__init__("News text must not be empty")


class ModelUnavailableError(AnalysisServiceError):
    def __init__(self, model_name: AnalysisModelName) -> None:
        self.model_name = model_name
        super().__init__(f"Analysis model is unavailable: {model_name}")
```

- [ ] **Step 5: Implement domain model**

Create `apps/analysis-service/src/analysis_service/domain/model.py`:

```python
from dataclasses import dataclass, field
from typing import Any

from analysis_service.domain.errors import EmptyNewsTextError
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel


@dataclass(frozen=True)
class NewsText:
    value: str

    @classmethod
    def from_raw(cls, value: str) -> "NewsText":
        normalized = value.strip()
        if not normalized:
            raise EmptyNewsTextError()
        return cls(value=normalized)


@dataclass(frozen=True)
class ImpactPrediction:
    model_name: AnalysisModelName
    impact: ImpactLabel
    confidence: float | None = None
    explanation: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.explanation is None:
            object.__setattr__(
                self,
                "explanation",
                f"Model classified the news text as {self.impact.value}.",
            )
```

- [ ] **Step 6: Implement application ports**

Create `apps/analysis-service/src/analysis_service/application/ports.py`:

```python
from typing import Protocol

from analysis_service.domain.model import ImpactPrediction, NewsText
from economic_news_contracts.analysis import AnalysisModelName


class ImpactClassifier(Protocol):
    model_name: AnalysisModelName

    def predict(self, text: NewsText) -> ImpactPrediction:
        """Predict economic impact for a normalized news text."""


class ModelRegistry(Protocol):
    def get(self, model_name: AnalysisModelName) -> ImpactClassifier:
        """Return classifier by model name or raise ModelUnavailableError."""
```

- [ ] **Step 7: Implement use case**

Create `apps/analysis-service/src/analysis_service/application/use_cases.py`:

```python
from analysis_service.application.ports import ModelRegistry
from analysis_service.domain.model import ImpactPrediction, NewsText
from economic_news_contracts.analysis import AnalysisModelName


class AnalyzeNewsImpact:
    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def execute(self, *, text: str, model_name: AnalysisModelName) -> ImpactPrediction:
        news_text = NewsText.from_raw(text)
        classifier = self._registry.get(model_name)
        return classifier.predict(news_text)
```

- [ ] **Step 8: Verify domain and use case**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_domain.py apps/analysis-service/tests/test_use_cases.py -v -W error
uv run ruff check apps/analysis-service
uv run ty check apps/analysis-service
```

Expected: all pass.

- [ ] **Step 9: Commit**

Run:

```bash
git add apps/analysis-service
git commit -m "feat: добавить домен analysis service"
```

---

### Task 3: Infrastructure Classifiers

**Files:**

- Create: `apps/analysis-service/src/analysis_service/infrastructure/classifiers.py`
- Create: `apps/analysis-service/tests/test_infrastructure.py`

- [ ] **Step 1: Write infrastructure tests**

Create `apps/analysis-service/tests/test_infrastructure.py`:

```python
from pathlib import Path

import joblib
import pytest

from analysis_service.domain.errors import ModelUnavailableError
from analysis_service.domain.model import NewsText
from analysis_service.infrastructure.classifiers import (
    JoblibImpactClassifier,
    StaticImpactClassifier,
    StaticModelRegistry,
)
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel


class FakeEstimator:
    def predict(self, texts: list[str]) -> list[str]:
        assert texts == ["Markets rise"]
        return ["positive"]


def test_static_classifier_returns_configured_prediction() -> None:
    classifier = StaticImpactClassifier(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        impact=ImpactLabel.NEUTRAL,
    )

    prediction = classifier.predict(NewsText.from_raw("Markets wait"))

    assert prediction.model_name == AnalysisModelName.TFIDF_LOGREG
    assert prediction.impact == ImpactLabel.NEUTRAL
    assert prediction.metadata == {"source": "static"}


def test_joblib_classifier_predicts_with_loaded_estimator(tmp_path: Path) -> None:
    model_path = tmp_path / "model.joblib"
    joblib.dump(FakeEstimator(), model_path)
    classifier = JoblibImpactClassifier(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        artifact_path=model_path,
    )

    prediction = classifier.predict(NewsText.from_raw("Markets rise"))

    assert prediction.model_name == AnalysisModelName.TFIDF_LOGREG
    assert prediction.impact == ImpactLabel.POSITIVE
    assert prediction.metadata == {"artifact_path": str(model_path)}


def test_joblib_classifier_reports_missing_artifact(tmp_path: Path) -> None:
    classifier = JoblibImpactClassifier(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        artifact_path=tmp_path / "missing.joblib",
    )

    with pytest.raises(ModelUnavailableError):
        classifier.predict(NewsText.from_raw("Markets rise"))


def test_static_registry_returns_classifier_by_name() -> None:
    classifier = StaticImpactClassifier(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        impact=ImpactLabel.POSITIVE,
    )
    registry = StaticModelRegistry([classifier])

    assert registry.get(AnalysisModelName.TFIDF_LOGREG) is classifier


def test_static_registry_reports_unknown_model() -> None:
    registry = StaticModelRegistry([])

    with pytest.raises(ModelUnavailableError):
        registry.get(AnalysisModelName.TFIDF_LOGREG)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_infrastructure.py -v
```

Expected: fail because infrastructure module is missing.

- [ ] **Step 3: Implement classifiers and registry**

Create `apps/analysis-service/src/analysis_service/infrastructure/classifiers.py`:

```python
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import joblib

from analysis_service.application.ports import ImpactClassifier
from analysis_service.domain.errors import ModelUnavailableError
from analysis_service.domain.model import ImpactPrediction, NewsText
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel


class StaticImpactClassifier:
    def __init__(
        self,
        *,
        model_name: AnalysisModelName,
        impact: ImpactLabel = ImpactLabel.NEUTRAL,
    ) -> None:
        self.model_name = model_name
        self._impact = impact

    def predict(self, text: NewsText) -> ImpactPrediction:
        return ImpactPrediction(
            model_name=self.model_name,
            impact=self._impact,
            metadata={"source": "static"},
        )


class JoblibImpactClassifier:
    def __init__(self, *, model_name: AnalysisModelName, artifact_path: Path) -> None:
        self.model_name = model_name
        self._artifact_path = artifact_path
        self._estimator: Any | None = None

    def predict(self, text: NewsText) -> ImpactPrediction:
        estimator = self._load_estimator()
        raw_prediction = estimator.predict([text.value])[0]
        return ImpactPrediction(
            model_name=self.model_name,
            impact=ImpactLabel(str(raw_prediction)),
            metadata={"artifact_path": str(self._artifact_path)},
        )

    def _load_estimator(self) -> Any:
        if self._estimator is not None:
            return self._estimator
        if not self._artifact_path.exists():
            raise ModelUnavailableError(self.model_name)
        self._estimator = joblib.load(self._artifact_path)
        return self._estimator


class StaticModelRegistry:
    def __init__(self, classifiers: Iterable[ImpactClassifier]) -> None:
        self._classifiers = {classifier.model_name: classifier for classifier in classifiers}

    def get(self, model_name: AnalysisModelName) -> ImpactClassifier:
        try:
            return self._classifiers[model_name]
        except KeyError as exc:
            raise ModelUnavailableError(model_name) from exc
```

- [ ] **Step 4: Verify infrastructure**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_infrastructure.py -v -W error
uv run ruff check apps/analysis-service
uv run ty check apps/analysis-service
```

Expected: all pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add apps/analysis-service
git commit -m "feat: добавить классификаторы analysis service"
```

---

### Task 4: FastAPI Presentation and Dishka Wiring

**Files:**

- Create: `apps/analysis-service/src/analysis_service/main/settings.py`
- Create: `apps/analysis-service/src/analysis_service/main/container.py`
- Create: `apps/analysis-service/src/analysis_service/main/app.py`
- Create: `apps/analysis-service/src/analysis_service/presentation/errors.py`
- Create: `apps/analysis-service/src/analysis_service/presentation/router.py`
- Create: `apps/analysis-service/tests/test_api.py`

- [ ] **Step 1: Write API tests**

Create `apps/analysis-service/tests/test_api.py`:

```python
from fastapi.testclient import TestClient

from analysis_service.main.app import create_app
from economic_news_contracts.analysis import AnalysisModelName


def test_analysis_service_health_endpoint() -> None:
    client = TestClient(create_app(use_static_classifier=True))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "analysis-service", "status": "ok"}


def test_analyze_endpoint_returns_prediction() -> None:
    client = TestClient(create_app(use_static_classifier=True))

    response = client.post(
        "/api/v1/analyze",
        json={
            "text": "Markets rise after strong earnings.",
            "analysis_model": AnalysisModelName.TFIDF_LOGREG,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "model_name": "tfidf-logreg",
        "impact": "neutral",
        "confidence": None,
        "explanation": "Model classified the news text as neutral.",
        "metadata": {"source": "static"},
    }


def test_analyze_endpoint_rejects_blank_text() -> None:
    client = TestClient(create_app(use_static_classifier=True))

    response = client.post(
        "/api/v1/analyze",
        json={"text": "   ", "analysis_model": AnalysisModelName.TFIDF_LOGREG},
    )

    assert response.status_code == 422


def test_analyze_endpoint_reports_unavailable_model() -> None:
    client = TestClient(create_app(use_static_classifier=True))

    response = client.post(
        "/api/v1/analyze",
        json={
            "text": "Markets rise after strong earnings.",
            "analysis_model": AnalysisModelName.EMBEDDING_LOGREG,
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Analysis model is unavailable: embedding-logreg",
    }
```

- [ ] **Step 2: Run API tests to verify failure**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_api.py -v
```

Expected: fail because app factory and router are missing.

- [ ] **Step 3: Implement settings**

Create `apps/analysis-service/src/analysis_service/main/settings.py`:

```python
from pathlib import Path

from economic_news_framework.settings import BaseServiceSettings
from pydantic_settings import SettingsConfigDict


class AnalysisServiceSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(env_prefix="ANALYSIS_")

    service_name: str = "analysis-service"
    version: str = "0.1.0"
    use_static_classifier: bool = False
    tfidf_artifact_path: Path = Path("artifacts/models/baseline/tfidf-logreg.joblib")
    embedding_artifact_path: Path = Path("artifacts/models/embedding/embedding-logreg.joblib")
    transformer_artifact_path: Path = Path(
        "artifacts/models/transformer/tiny-transformer-classifier.joblib",
    )
```

- [ ] **Step 4: Implement container wiring**

Create `apps/analysis-service/src/analysis_service/main/container.py`:

```python
from analysis_service.application.ports import ModelRegistry
from analysis_service.application.use_cases import AnalyzeNewsImpact
from analysis_service.infrastructure.classifiers import (
    JoblibImpactClassifier,
    StaticImpactClassifier,
    StaticModelRegistry,
)
from analysis_service.main.settings import AnalysisServiceSettings
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel


class AnalysisServiceProvider(Provider):
    def __init__(self, settings: AnalysisServiceSettings | None = None) -> None:
        super().__init__()
        self._settings = settings

    @provide(scope=Scope.APP)
    def settings(self) -> AnalysisServiceSettings:
        return self._settings or AnalysisServiceSettings()

    @provide(scope=Scope.APP)
    def model_registry(self, settings: AnalysisServiceSettings) -> ModelRegistry:
        if settings.use_static_classifier:
            return StaticModelRegistry(
                [
                    StaticImpactClassifier(
                        model_name=AnalysisModelName.TFIDF_LOGREG,
                        impact=ImpactLabel.NEUTRAL,
                    ),
                ],
            )
        return StaticModelRegistry(
            [
                JoblibImpactClassifier(
                    model_name=AnalysisModelName.TFIDF_LOGREG,
                    artifact_path=settings.tfidf_artifact_path,
                ),
                JoblibImpactClassifier(
                    model_name=AnalysisModelName.EMBEDDING_LOGREG,
                    artifact_path=settings.embedding_artifact_path,
                ),
                JoblibImpactClassifier(
                    model_name=AnalysisModelName.TINY_TRANSFORMER_CLASSIFIER,
                    artifact_path=settings.transformer_artifact_path,
                ),
            ],
        )

    @provide(scope=Scope.APP)
    def analyze_news_impact(self, registry: ModelRegistry) -> AnalyzeNewsImpact:
        return AnalyzeNewsImpact(registry)


def create_container(settings: AnalysisServiceSettings | None = None):
    return make_async_container(AnalysisServiceProvider(settings), FastapiProvider())
```

- [ ] **Step 5: Implement error mapping**

Create `apps/analysis-service/src/analysis_service/presentation/errors.py`:

```python
from analysis_service.domain.errors import EmptyNewsTextError, ModelUnavailableError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(EmptyNewsTextError)
    async def empty_news_text_handler(
        request: Request,
        exc: EmptyNewsTextError,
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ModelUnavailableError)
    async def model_unavailable_handler(
        request: Request,
        exc: ModelUnavailableError,
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})
```

- [ ] **Step 6: Implement router**

Create `apps/analysis-service/src/analysis_service/presentation/router.py`:

```python
from analysis_service.application.use_cases import AnalyzeNewsImpact
from dishka.integrations.fastapi import FromDishka, inject
from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


@router.post("/analyze")
@inject
async def analyze(
    request: AnalyzeNewsRequest,
    use_case: FromDishka[AnalyzeNewsImpact],
) -> AnalyzeNewsResponse:
    prediction = use_case.execute(
        text=request.text,
        model_name=request.analysis_model,
    )
    return AnalyzeNewsResponse(
        model_name=prediction.model_name,
        impact=prediction.impact,
        confidence=prediction.confidence,
        explanation=prediction.explanation or "",
        metadata=prediction.metadata,
    )
```

- [ ] **Step 7: Implement app factory**

Create `apps/analysis-service/src/analysis_service/main/app.py`:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from analysis_service.main.container import create_container
from analysis_service.main.settings import AnalysisServiceSettings
from analysis_service.presentation.errors import register_error_handlers
from analysis_service.presentation.router import router
from dishka.integrations.fastapi import setup_dishka
from economic_news_framework.apps import create_service_app
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.dishka_container.close()


def create_app(*, use_static_classifier: bool | None = None) -> FastAPI:
    settings = AnalysisServiceSettings()
    if use_static_classifier is not None:
        settings.use_static_classifier = use_static_classifier
    container = create_container(settings)
    app = create_service_app(
        service_name=settings.service_name,
        routers=(router,),
        log_level=settings.log_level,
    )
    app.router.lifespan_context = lifespan
    setup_dishka(container=container, app=app)
    register_error_handlers(app)
    return app


app = create_app()
```

- [ ] **Step 8: Verify API**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_api.py -v -W error
uv run ruff check apps/analysis-service
uv run ty check apps/analysis-service
```

Expected: all pass.

- [ ] **Step 9: Commit**

Run:

```bash
git add apps/analysis-service
git commit -m "feat: добавить api analysis service"
```

---

### Task 5: Runtime Integration

**Files:**

- Modify: `Justfile`
- Modify: `deploy/compose.yaml`
- Create: `deploy/docker/analysis-service.Dockerfile`
- Modify: `README.md` if startup commands need to mention the new service

- [ ] **Step 1: Write Dockerfile**

Create `deploy/docker/analysis-service.Dockerfile` by following the existing API gateway image pattern and changing the package/app names:

```dockerfile
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
```

- [ ] **Step 2: Add Compose service**

Update `deploy/compose.yaml`:

```yaml
  analysis-service:
    build:
      context: ..
      dockerfile: deploy/docker/analysis-service.Dockerfile
    env_file:
      - ../.env.example
    environment:
      ANALYSIS_USE_STATIC_CLASSIFIER: "true"
    ports:
      - "8001:8000"
```

Do not add dependencies on PostgreSQL, Redis, Qdrant, or MLflow for this service.

- [ ] **Step 3: Add Justfile command**

Update `Justfile`:

```make
analysis-dev:
    ANALYSIS_USE_STATIC_CLASSIFIER=true uv run --package economic-news-analysis-service granian analysis_service.main.app:app --interface asgi --host 0.0.0.0 --port 8001
```

- [ ] **Step 4: Verify runtime files**

Run:

```bash
uv run ruff check apps packages
uv run ty check apps packages
uv run pytest packages apps -v -W error
```

Expected: all pass.

If Docker is available, run:

```bash
docker compose -f deploy/compose.yaml build analysis-service
```

Expected: image builds successfully.

- [ ] **Step 5: Commit**

Run:

```bash
git add Justfile deploy README.md
git commit -m "feat: добавить запуск analysis service"
```

---

### Task 6: Final Verification and PR

**Files:**

- No planned source edits unless verification finds a concrete issue.

- [ ] **Step 1: Run full verification**

Run:

```bash
uv run ruff check apps packages research
uv run ty check apps packages research
uv run pytest packages apps research/tests -v -W error
```

Expected: all pass.

- [ ] **Step 2: Check worktree**

Run:

```bash
git status --short
```

Expected: no unstaged or uncommitted implementation changes.

- [ ] **Step 3: Dispatch final code review**

Review diff from `dev` to `feature/analysis-service` with focus on:

- service follows approved DDD layer boundaries;
- contracts use real model names;
- endpoint returns controlled errors;
- no unused Redis, Taskiq, FastStream, Qdrant, PostgreSQL, SSE, UI, or LLM code was added;
- tests do not download model weights.

- [ ] **Step 4: Push branch**

Run:

```bash
git push -u origin feature/analysis-service
```

- [ ] **Step 5: Create PR**

Run:

```bash
gh pr create --base dev --head feature/analysis-service --title "feat: добавить analysis service" --body "## Что сделано
- Добавлен микросервис analysis-service.
- Добавлены контракты анализа экономических новостей.
- Добавлены DDD слои, Dishka wiring, FastAPI endpoint и joblib classifier loading.
- Добавлен локальный запуск через Granian и Docker Compose.

## Проверки
- uv run ruff check apps packages research
- uv run ty check apps packages research
- uv run pytest packages apps research/tests -v -W error"
```

---

## Self-Review

- Spec coverage: tasks cover contracts, service structure, domain, application, infrastructure, HTTP presentation, runtime integration, and final verification.
- Scope check: no task adds Redis, Taskiq, FastStream, Qdrant, PostgreSQL, SSE, React UI, llama.cpp, or MLflow management.
- Type consistency: contract enum values are reused across domain, use case, infrastructure, and API tests.
- Test strategy: tests use fake/static classifiers and joblib fake estimators, with no model downloads.

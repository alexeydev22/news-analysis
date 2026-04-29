# Design: analysis-service

## 1. Goal

`analysis-service` is the first core backend microservice after the research slice. It exposes economic news impact classification as a production-style FastAPI service while staying small enough for coursework implementation and local development.

The service answers one question:

> What is the expected economic impact of this news text according to the selected analysis model?

It does not store news, perform semantic retrieval, call the local LLM, manage MLflow experiments, or orchestrate user chat. Those responsibilities belong to later services.

## 2. Scope

Included in this slice:

- a new `apps/analysis-service` microservice;
- shared analysis request/response contracts in `packages/contracts`;
- DDD-oriented service structure with `domain`, `application`, `infrastructure`, `presentation`, `main`, and `workers`;
- FastAPI endpoint `POST /api/v1/analyze`;
- Dishka-based dependency wiring;
- Protocol-based application interfaces;
- joblib model loading for research artifacts;
- deterministic fake classifiers for tests;
- Dockerfile and Compose entry for local service startup;
- Justfile command for local Granian startup if the existing pattern supports it.

Excluded from this slice:

- PostgreSQL persistence;
- Qdrant retrieval;
- Redis, Taskiq, FastStream workers;
- SSE streaming;
- llama.cpp dialog generation;
- React UI;
- automatic model training;
- MLflow experiment management.

This keeps the PR focused on a working service boundary instead of building architecture that is not used yet.

## 3. Model Names

The current research pipeline produces these model names:

- `tfidf-logreg`;
- `embedding-logreg`;
- `tiny-transformer-classifier`.

`packages/contracts` should align `AnalysisModelName` with these real artifact names. Older placeholder names such as `rubert-tiny2-classifier` and `rubert-tiny2-finetuned` should not be used in the API contract unless actual artifacts with those names exist.

## 4. API Contract

Request DTO:

```json
{
  "text": "Central bank keeps rates unchanged while inflation slows.",
  "analysis_model": "tfidf-logreg"
}
```

Response DTO:

```json
{
  "model_name": "tfidf-logreg",
  "impact": "neutral",
  "confidence": null,
  "explanation": "Model classified the news text as neutral.",
  "metadata": {}
}
```

Validation rules:

- `text` must be non-empty after trimming;
- `analysis_model` must be one of `AnalysisModelName`;
- unavailable models should return a controlled HTTP error, not an unhandled traceback.

## 5. Service Structure

```text
apps/analysis-service/
  src/analysis_service/
    domain/
      model.py
      errors.py
    application/
      ports.py
      use_cases.py
    infrastructure/
      classifiers.py
    presentation/
      router.py
      errors.py
    main/
      settings.py
      container.py
      app.py
    workers/
      __init__.py
  tests/
    test_domain.py
    test_use_cases.py
    test_api.py
```

Layer responsibilities:

- `domain`: value objects and service-specific domain errors;
- `application`: use cases and `typing.Protocol` ports;
- `infrastructure`: concrete classifier registry and joblib loading;
- `presentation`: FastAPI routes and HTTP error mapping;
- `main`: settings, Dishka providers, app factory;
- `workers`: empty package for consistency, no background tasks in this slice.

## 6. Domain Model

`NewsText` validates and stores normalized text.

`ImpactPrediction` stores:

- selected model name;
- predicted `ImpactLabel`;
- optional confidence score;
- short explanation;
- metadata dictionary.

Domain errors:

- empty news text;
- unavailable model.

No generic repositories, factories, or domain events are needed for this slice.

## 7. Application Layer

Ports:

```python
class ImpactClassifier(Protocol):
    model_name: AnalysisModelName

    def predict(self, text: NewsText) -> ImpactPrediction: ...


class ModelRegistry(Protocol):
    def get(self, model_name: AnalysisModelName) -> ImpactClassifier: ...
```

Use case:

```python
class AnalyzeNewsImpact:
    def __init__(self, registry: ModelRegistry) -> None: ...

    def execute(self, text: str, model_name: AnalysisModelName) -> ImpactPrediction: ...
```

The use case validates text via `NewsText`, gets the requested classifier from the registry, and returns the classifier prediction.

## 8. Infrastructure

Two classifier implementations are enough:

1. `StaticImpactClassifier` for tests and fallback wiring.
2. `JoblibImpactClassifier` for real artifacts.

`JoblibImpactClassifier` loads an estimator from a `.joblib` path and calls `predict([text])`. It should support artifacts created by:

- baseline pipeline;
- embedding text classifier;
- tiny transformer trainer, if serialized successfully.

The registry maps `AnalysisModelName` to classifier instances. Missing paths raise `ModelUnavailableError`.

Default artifact paths should be settings-based and local:

```text
artifacts/models/baseline/tfidf-logreg.joblib
artifacts/models/embedding/embedding-logreg.joblib
artifacts/models/transformer/tiny-transformer-classifier.joblib
```

## 9. Presentation Layer

Endpoint:

```text
POST /api/v1/analyze
```

Behavior:

- validates request DTO through Pydantic;
- calls `AnalyzeNewsImpact`;
- returns response DTO;
- maps empty text to `422`;
- maps unavailable model to `503`;
- does not expose internal paths or Python exception details.

`/health` remains provided by `economic_news_framework.create_service_app`.

## 10. Settings and Runtime

Settings:

- `service_name = "analysis-service"`;
- `version = "0.1.0"`;
- model artifact paths;
- `use_static_classifier` flag for local/demo startup when artifacts are not present.

Runtime:

- local command uses Granian;
- Dockerfile follows the existing `api-gateway` image pattern;
- Compose adds `analysis-service` on a separate port, for example `8001:8000`.

## 11. Testing

Required tests:

- `NewsText` rejects blank text and trims valid text;
- `AnalyzeNewsImpact` selects the requested model through a registry;
- unavailable model produces a domain/application error;
- API returns successful analysis response;
- API maps unavailable model to a controlled HTTP status;
- app factory exposes `/health`.

Unit tests must not download transformer or embedding weights. Use static/fake classifiers for service tests.

## 12. Acceptance Criteria

- `apps/analysis-service` follows the established microservice structure.
- Contracts expose request/response DTOs and current model enum values.
- `POST /api/v1/analyze` works with a deterministic classifier in tests.
- Production wiring can load joblib artifacts from local `artifacts/models`.
- Missing artifacts fail with a clear controlled error.
- `uv run ruff check apps packages research` passes.
- `uv run ty check apps packages research` passes.
- `uv run pytest packages apps research/tests -v -W error` passes.
- The implementation remains focused: no unused Redis, Taskiq, FastStream, Qdrant, or database code in this slice.

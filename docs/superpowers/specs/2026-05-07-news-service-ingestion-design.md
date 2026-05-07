# News Service Ingestion Design

## Goal

Add a lean `news-service` microservice that loads economic news from a local CSV dataset, normalizes records into stable news documents, previews them through HTTP, and sends batches to `retrieval-service` for indexing in Qdrant.

This fills the current data-ingestion gap in the coursework system. The project already has analysis, retrieval, dialog and SSE chat flow; this slice adds the missing source of news data without introducing PostgreSQL, Redis workers or background job orchestration yet.

## Scope

In scope:

- new `apps/news-service` package following the existing DDD/layered layout;
- CSV adapter for local files under `data/raw` or an explicit configured path;
- deterministic normalization into news documents:
  - stable `id`;
  - non-empty `title`;
  - non-empty `text`;
  - non-empty `source`;
  - optional `published_at`;
  - metadata with useful non-core fields;
- `GET /api/v1/news/preview?limit=...`;
- `POST /api/v1/news/index`;
- Zapros client from `news-service` to `retrieval-service`;
- contracts for news preview/indexing API;
- Dockerfile and compose entry for `news-service`;
- README updates for local ingestion demo.

Out of scope:

- PostgreSQL persistence;
- Taskiq/FastStream/Redis background jobs;
- fresh online news scraping;
- authentication;
- UI changes;
- changing `retrieval-service` semantics except contracts needed for client compatibility;
- analysis or dialog calls from `news-service`.

## Input Dataset Contract

The service reads CSV files with a tolerant column mapping. Required semantic fields:

- title: one of `title`, `headline`;
- text: one of `text`, `content`, `body`, `description`;
- source: one of `source`, `publisher`;

Optional fields:

- id: one of `id`, `news_id`, `article_id`;
- published_at: one of `published_at`, `date`, `published`;
- label/impact fields are kept in metadata, not used for indexing decisions.

Rows with missing required semantic fields are rejected during load. For the first version, a single bad row should make the load fail with a domain validation error rather than silently dropping data.

If source row has no id, generate a stable id from normalized `source`, `title` and `text` using UUIDv5 or SHA-256 prefix. The same CSV row must produce the same id across runs.

## API Contract

### `GET /api/v1/news/preview`

Query parameters:

- `limit`: integer, default `10`, min `1`, max `100`.

Response:

```json
{
  "documents": [
    {
      "id": "demo-1",
      "title": "GDP growth beats expectations",
      "text": "Gross domestic product grew by 2 percent...",
      "source": "demo",
      "published_at": null,
      "metadata": {
        "row_number": 2,
        "impact": "positive"
      }
    }
  ],
  "total_count": 25
}
```

The endpoint returns normalized documents from the configured CSV source. `total_count` reports all normalized rows, not only the preview count.

### `POST /api/v1/news/index`

Request:

```json
{
  "limit": 100
}
```

Fields:

- `limit`: optional integer, default `100`, min `1`, max `1000`.

Response:

```json
{
  "loaded_count": 25,
  "indexed_count": 25,
  "collection_name": "economic_news"
}
```

The use case loads up to `limit` normalized documents and delegates indexing to `retrieval-service` through the existing retrieval indexing contract.

## Architecture

`news-service` follows the same layered pattern as the other backend services:

```text
apps/news-service/src/news_service/
  domain/
    model.py
    errors.py
  application/
    ports.py
    use_cases.py
  infrastructure/
    csv_news_source.py
    retrieval_client.py
  presentation/
    router.py
    errors.py
  main/
    app.py
    container.py
    settings.py
  workers/
    __init__.py
```

Domain:

- `NewsDocument`: immutable normalized document;
- domain errors for empty fields, missing columns and unavailable ingestion source.

Application:

- `NewsSource` Protocol with `load(limit: int | None) -> list[NewsDocument]`;
- `RetrievalIndexer` Protocol with `index(documents: list[NewsDocument]) -> IndexNewsResponse`;
- `PreviewNews` use case;
- `IndexNewsDataset` use case.

Infrastructure:

- `CsvNewsSource` reads and validates CSV using Python stdlib `csv` to avoid new dependencies;
- `ZaprosRetrievalIndexer` calls `retrieval-service` `POST /api/v1/retrieval/index`;
- infrastructure errors are mapped to domain/application unavailable errors.

Presentation:

- FastAPI routes map contracts to use cases;
- internal paths, file-system errors and transport details are not exposed.

## Contracts

Add `packages/contracts/src/economic_news_contracts/news.py`:

- `NewsDocumentResponse`;
- `PreviewNewsResponse`;
- `IndexNewsDatasetRequest`;
- `IndexNewsDatasetResponse`.

These contracts are for external `news-service` API. For indexing, `news-service` converts domain documents into existing `NewsDocumentPayload` and `IndexNewsRequest`.

## Settings

`NewsServiceSettings`:

- `service_name = "news-service"`;
- `news_dataset_path`: default `data/raw/economic_news.csv`;
- `retrieval_service_url`: default `http://retrieval-service:8000`;
- `retrieval_service_timeout_seconds`: default `10.0`;
- `default_index_limit`: default `100`.

Environment prefix:

```text
NEWS_SERVICE_
```

Examples:

```bash
NEWS_SERVICE_NEWS_DATASET_PATH=data/raw/news_impact_sample.csv
NEWS_SERVICE_RETRIEVAL_SERVICE_URL=http://localhost:8002
```

## Docker Compose

Add `news-service` to `deploy/compose.yaml`:

- builds from `deploy/docker/news-service.Dockerfile`;
- exposes port `8004:8000`;
- depends on `retrieval-service`;
- mounts or uses repository `data/` path for local CSV availability in development;
- receives `NEWS_SERVICE_RETRIEVAL_SERVICE_URL=http://retrieval-service:8000`.

Add `deploy/docker/news-service.Dockerfile` using the same slim style as existing service Dockerfiles and Granian startup.

## Error Handling

HTTP mappings:

- invalid CSV shape or empty required data -> `422`;
- missing dataset file -> `503` with `news source is unavailable`;
- retrieval-service unavailable -> `503` with `retrieval-service is unavailable`;
- unexpected infrastructure details are hidden.

The service should not expose absolute local paths in API errors.

## Testing

Required tests:

- contract tests for new news DTOs;
- domain tests for trimming, required fields and stable generated ids;
- CSV adapter tests:
  - reads supported column aliases;
  - rejects missing required semantic columns;
  - rejects empty required row fields;
  - preserves extra fields in metadata;
- use-case tests for preview and index orchestration;
- Zapros retrieval client tests for payload shape and unavailable error mapping;
- API route tests for preview, index and error mapping;
- container/settings tests;
- compose config test by command.

## Verification

Run:

```bash
uv run ruff check apps packages research
uv run ty check apps packages research
uv run pytest packages apps research/tests -v -W error
docker compose -f deploy/compose.yaml config
```

If Docker daemon is available:

```bash
docker compose -f deploy/compose.yaml build news-service
```

## Coursework Fit

This slice supports:

- data preparation and source description in chapter 2;
- microservice architecture in chapter 4;
- demonstration scenario where the system first indexes local economic news and then answers questions through retrieval, analysis and dialog services.

It is intentionally lean: it gives a real ingestion boundary and reproducible local demo without adding background infrastructure before the synchronous data flow is clear.

# E2E Demo Scenario Design

## Goal

Add a lean, reproducible demo scenario for coursework defense that proves the
microservice stack can load economic news, index them, stream a dialog answer,
and serve the React console.

## Scope

This slice adds demo data, local commands, and a smoke script. It does not add
new business logic, authentication, synthetic monitoring, or a separate
orchestrator service.

## Architecture

The demo remains outside service internals:

- `data/raw/economic_news.csv` provides a small stable dataset for local runs.
- `tools/demo_smoke.py` is a CLI smoke checker that calls already existing HTTP
  endpoints and parses SSE events from `api-gateway`.
- `justfile` exposes `demo-up`, `demo-smoke`, and `demo-down` commands.
- `README.md` documents a single defense-ready demo flow.

The script uses only Python standard library HTTP APIs so it does not expand the
runtime stack.

## Demo Flow

1. Start Docker Compose with all services.
2. Check `api-gateway` and `news-service` health.
3. Preview news from `news-service`.
4. Index demo news synchronously through `POST /api/v1/news/index` so the chat
   path is deterministic.
5. Queue background indexing through `POST /api/v1/news/index/jobs` to verify
   Taskiq/Redis wiring.
6. Call `POST /api/v1/chat/stream` and verify key SSE events are present.
7. Optionally verify the frontend URL returns HTML.

## Error Handling

The smoke script fails fast with a clear message:

- non-2xx HTTP response;
- malformed JSON response;
- missing expected SSE event;
- connection failure or timeout.

The script prints concise progress lines suitable for terminal demos.

## Testing

Unit tests cover URL joining and SSE parsing helpers without requiring Docker.
Final verification includes repository tests, frontend tests, compose config,
and Docker image build for the services affected by the demo flow.

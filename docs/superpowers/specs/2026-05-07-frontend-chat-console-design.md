# Design: Frontend Chat Console

Дата: 2026-05-07

## 1. Goal

Add a lean React UI for the coursework demo. The first screen must be the actual
dialog system console: ask a question, stream the answer, show pipeline stages,
show retrieved sources, show economic impact summaries, switch the analysis
model, and run local CSV preview/index actions.

The UI is not a landing page and not a generic dashboard. It is a work-focused
single-page tool that demonstrates the project topic: a language-model-based
dialog system for economic-news analysis.

## 2. Scope

In scope:

- new `frontend/web` Vite application;
- React + TypeScript + CSS Modules;
- real backend API calls only;
- chat streaming through `POST /api/v1/chat/stream`;
- news preview through `GET /api/v1/news/preview`;
- news indexing through `POST /api/v1/news/index`;
- model switcher for `analysis_model`;
- source and impact-summary panels;
- clear loading, empty, success and error states;
- Dockerfile and Compose entry for the web UI;
- README and Justfile commands for local frontend development.

Out of scope:

- mock fallback data;
- auth;
- routing;
- server-side rendering;
- UI component library;
- charting library;
- generated marketing hero page;
- editing backend contracts.

## 3. UX Direction

Chosen direction: chat-first console.

Layout:

- left rail: system controls;
- center: question input, streaming answer and event timeline;
- right rail: retrieved sources and impact summaries.

The page should feel like an analytical operator console, not a promo site:
dense but readable, restrained colors, predictable controls, no decorative
cards inside cards, no oversized hero section. Cards are used only for repeated
source/summary items and have small radii.

The first viewport must show usable controls immediately:

- analysis model selector;
- result limit;
- source filter;
- preview/index dataset actions;
- question input;
- answer panel;
- sources panel.

## 4. Runtime Configuration

Frontend uses environment variables:

- `VITE_API_GATEWAY_URL`, default `http://localhost:8000`;
- `VITE_NEWS_SERVICE_URL`, default `http://localhost:8004`.

No mock mode exists. If a backend service is down, the UI shows a concise error
with the affected action and keeps the current state visible.

## 5. API Integration

### Chat Stream

The UI sends:

```json
{
  "question": "Что означает рост ВВП для рынка?",
  "analysis_model": "tfidf-logreg",
  "limit": 5,
  "source": null
}
```

to:

```text
POST {VITE_API_GATEWAY_URL}/api/v1/chat/stream
Accept: text/event-stream
Content-Type: application/json
```

The response is parsed as SSE text from `ReadableStream`. `EventSource` is not
used because the endpoint is `POST`.

Expected events:

- `chat_started`;
- `search_started`;
- `sources_found`;
- `analysis_started`;
- `analysis_completed`;
- `answer_started`;
- `answer_completed`;
- `done`;
- `error`.

The UI displays event order as a compact timeline. `answer_completed` updates
the answer, sources and impact summaries. `error` shows sanitized failure text.

### News Preview

The UI calls:

```text
GET {VITE_NEWS_SERVICE_URL}/api/v1/news/preview?limit=5
```

and shows a compact table/list with title, source, published date and metadata.

### News Index

The UI calls:

```text
POST {VITE_NEWS_SERVICE_URL}/api/v1/news/index
Content-Type: application/json
```

with:

```json
{"limit": 100}
```

The UI shows loaded count, indexed count and collection name.

## 6. Frontend Structure

Files:

```text
frontend/web/
  package.json
  index.html
  tsconfig.json
  tsconfig.node.json
  vite.config.ts
  src/
    main.tsx
    app/App.tsx
    app/App.module.css
    app/types.ts
    api/config.ts
    api/chatStream.ts
    api/news.ts
    components/ControlsPanel.tsx
    components/ChatPanel.tsx
    components/SourcesPanel.tsx
    components/Timeline.tsx
    components/NewsPreview.tsx
    components/StatusMessage.tsx
    test/
      setup.ts
      fixtures.ts
```

Boundaries:

- `api/` owns HTTP and stream parsing;
- `app/` owns state orchestration;
- `components/` are presentational or narrowly interactive;
- no component imports backend URLs directly.

## 7. State Model

Application state:

- selected `analysisModel`;
- `limit`;
- optional `source`;
- `question`;
- stream `events`;
- current `answer`;
- `sources`;
- `impactSummaries`;
- preview documents;
- last index result;
- loading flags by action;
- current error message.

The app uses React state/hooks only. No TanStack Query is added in this slice.

## 8. Error Handling

Rules:

- network failure: show `Не удалось подключиться к сервису`;
- non-2xx JSON response with `detail`: show that sanitized detail;
- malformed stream event: show `Некорректный ответ stream API`;
- user can submit again after an error;
- existing answer/sources are not cleared until a new request starts.

No backend internal details, stack traces or local paths are displayed.

## 9. Testing

Frontend tests use Vitest and React Testing Library.

Required coverage:

- app renders controls and empty state;
- user can change model and submit a question;
- chat stream parser reads SSE chunks and returns typed events;
- stream error event is rendered as an error state;
- preview action renders returned documents;
- index action renders count result;
- API clients surface sanitized failures.

Verification commands:

```bash
npm --prefix frontend/web test -- --run
npm --prefix frontend/web run lint
npm --prefix frontend/web run typecheck
npm --prefix frontend/web run build
```

## 10. Infrastructure

Docker Compose adds `frontend-web`:

- builds from `deploy/docker/frontend-web.Dockerfile`;
- serves Vite build through nginx or a lightweight static server;
- exposes port `5173`;
- receives `VITE_API_GATEWAY_URL` and `VITE_NEWS_SERVICE_URL` at build time.

Local development:

```bash
npm --prefix frontend/web install
npm --prefix frontend/web run dev -- --host 0.0.0.0 --port 5173
```

Justfile adds:

```text
web-dev
web-test
web-build
```

## 11. Acceptance Criteria

- UI starts with Vite and shows the chat-first console.
- User can run real preview/index calls against `news-service`.
- User can send a real chat streaming request through `api-gateway`.
- Model selector sends `analysis_model` in the request.
- SSE events update timeline and final answer state.
- Sources and impact summaries are visible after a successful chat.
- Backend-down failures are visible and sanitized.
- No mock fallback, auth, routing or UI library is added.
- Tests, typecheck, lint and build pass locally.

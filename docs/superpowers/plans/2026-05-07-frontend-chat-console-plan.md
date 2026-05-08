# Frontend Chat Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lean Vite React UI that demonstrates the real economic-news dialog pipeline through backend APIs.

**Architecture:** The frontend is a single-page chat-first console in `frontend/web`. API modules own HTTP and SSE parsing, `app/` owns state orchestration, and components stay focused on rendering controls, answer, timeline, sources, preview and indexing status. The UI uses real `api-gateway` and `news-service` endpoints only; no mock fallback is added.

**Tech Stack:** Vite, React, TypeScript, CSS Modules, Vitest, React Testing Library, nginx static Docker image.

---

## File Structure

- Create `frontend/web/package.json`
  - npm scripts and frontend dependencies.
- Create `frontend/web/index.html`
  - Vite HTML entry.
- Create `frontend/web/tsconfig.json`
  - Browser TypeScript configuration.
- Create `frontend/web/tsconfig.node.json`
  - Vite config TypeScript configuration.
- Create `frontend/web/vite.config.ts`
  - React plugin and Vitest jsdom setup.
- Create `frontend/web/src/main.tsx`
  - React mount entrypoint.
- Create `frontend/web/src/app/types.ts`
  - UI-side DTOs matching backend contracts.
- Create `frontend/web/src/api/config.ts`
  - Runtime URL helpers.
- Create `frontend/web/src/api/errors.ts`
  - Sanitized API error type and response parser.
- Create `frontend/web/src/api/chatStream.ts`
  - `POST /api/v1/chat/stream` client and SSE parser.
- Create `frontend/web/src/api/news.ts`
  - `news-service` preview/index clients.
- Create `frontend/web/src/app/App.tsx`
  - Main state orchestration.
- Create `frontend/web/src/app/App.module.css`
  - Responsive console layout and visual styling.
- Create `frontend/web/src/components/ControlsPanel.tsx`
  - Model, limit, source, preview/index controls.
- Create `frontend/web/src/components/ChatPanel.tsx`
  - Question form, answer panel and error state.
- Create `frontend/web/src/components/Timeline.tsx`
  - Stream event timeline.
- Create `frontend/web/src/components/SourcesPanel.tsx`
  - Sources and impact summaries.
- Create `frontend/web/src/components/NewsPreview.tsx`
  - Dataset preview and index result.
- Create `frontend/web/src/components/StatusMessage.tsx`
  - Small reusable status block.
- Create `frontend/web/src/test/setup.ts`
  - Testing Library setup.
- Create `frontend/web/src/test/fixtures.ts`
  - Shared test fixtures.
- Create `frontend/web/src/api/chatStream.test.ts`
  - SSE parser/client tests.
- Create `frontend/web/src/api/news.test.ts`
  - News API client tests.
- Create `frontend/web/src/app/App.test.tsx`
  - App interaction tests.
- Modify `README.md`
  - Add frontend local run commands.
- Modify `justfile`
  - Add frontend development/test/build commands.
- Modify `deploy/compose.yaml`
  - Add `frontend-web`.
- Create `deploy/docker/frontend-web.Dockerfile`
  - Build static frontend and serve it.
- Create `deploy/docker/frontend-web.nginx.conf`
  - SPA static server config.

---

### Task 1: Frontend Scaffold and Test Harness

**Files:**
- Create: `frontend/web/package.json`
- Create: `frontend/web/index.html`
- Create: `frontend/web/tsconfig.json`
- Create: `frontend/web/tsconfig.node.json`
- Create: `frontend/web/vite.config.ts`
- Create: `frontend/web/src/main.tsx`
- Create: `frontend/web/src/app/App.tsx`
- Create: `frontend/web/src/app/App.module.css`
- Create: `frontend/web/src/test/setup.ts`
- Create: `frontend/web/src/app/App.test.tsx`
- Delete: `frontend/web/.gitkeep`

- [ ] **Step 1: Create package and config files**

Create `frontend/web/package.json`:

```json
{
  "name": "economic-news-web",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "tsc --noEmit",
    "typecheck": "tsc --noEmit",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^5.0.0",
    "vite": "^7.0.0",
    "typescript": "^5.8.0",
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/react": "^16.2.0",
    "@testing-library/user-event": "^14.6.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "jsdom": "^26.0.0",
    "vitest": "^3.0.0"
  }
}
```

Create `frontend/web/index.html`:

```html
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Economic News Dialog Console</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `frontend/web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2022"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

Create `frontend/web/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

Create `frontend/web/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["src/test/setup.ts"],
  },
});
```

- [ ] **Step 2: Create the first failing render test**

Create `frontend/web/src/app/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App", () => {
  it("renders the chat console controls and empty state", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Economic News Dialog" })).toBeInTheDocument();
    expect(screen.getByLabelText("Модель анализа")).toBeInTheDocument();
    expect(screen.getByLabelText("Лимит источников")).toBeInTheDocument();
    expect(screen.getByLabelText("Источник")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Preview CSV" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Index CSV" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Вопрос" })).toBeInTheDocument();
    expect(screen.getByText("Ответ появится после отправки вопроса.")).toBeInTheDocument();
  });
});
```

Create `frontend/web/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 3: Run the test and verify it fails**

Run:

```bash
npm --prefix frontend/web install
npm --prefix frontend/web test -- --run src/app/App.test.tsx
```

Expected: fail because `src/app/App.tsx` does not exist yet.

- [ ] **Step 4: Implement minimal App shell**

Create `frontend/web/src/app/App.tsx`:

```tsx
import styles from "./App.module.css";

export function App() {
  return (
    <main className={styles.shell}>
      <aside className={styles.controls}>
        <p className={styles.eyebrow}>Local RAG pipeline</p>
        <h1>Economic News Dialog</h1>

        <label className={styles.field}>
          <span>Модель анализа</span>
          <select aria-label="Модель анализа" defaultValue="tfidf-logreg">
            <option value="tfidf-logreg">tfidf-logreg</option>
            <option value="embedding-logreg">embedding-logreg</option>
            <option value="tiny-transformer">tiny-transformer</option>
          </select>
        </label>

        <label className={styles.field}>
          <span>Лимит источников</span>
          <input aria-label="Лимит источников" type="number" min={1} max={20} defaultValue={5} />
        </label>

        <label className={styles.field}>
          <span>Источник</span>
          <input aria-label="Источник" placeholder="all sources" />
        </label>

        <div className={styles.actions}>
          <button type="button">Preview CSV</button>
          <button type="button">Index CSV</button>
        </div>
      </aside>

      <section className={styles.chat}>
        <label className={styles.field}>
          <span>Вопрос</span>
          <textarea aria-label="Вопрос" rows={4} placeholder="Что означает рост ВВП?" />
        </label>
        <button type="button">Ask</button>
        <section className={styles.answer}>Ответ появится после отправки вопроса.</section>
      </section>

      <aside className={styles.sources}>
        <h2>Sources</h2>
        <p>Источники появятся после ответа.</p>
      </aside>
    </main>
  );
}
```

Create `frontend/web/src/app/App.module.css`:

```css
:global(*) {
  box-sizing: border-box;
}

:global(body) {
  margin: 0;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #f3f5f4;
  color: #17201b;
}

button,
input,
select,
textarea {
  font: inherit;
}

.shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(240px, 300px) minmax(360px, 1fr) minmax(280px, 360px);
  gap: 1px;
  background: #cfd8d3;
}

.controls,
.chat,
.sources {
  background: #f8faf8;
  padding: 24px;
}

.eyebrow {
  margin: 0 0 8px;
  color: #53645b;
  font-size: 0.78rem;
  text-transform: uppercase;
}

h1,
h2 {
  margin: 0 0 20px;
  letter-spacing: 0;
}

.field {
  display: grid;
  gap: 6px;
  margin-bottom: 16px;
  color: #34443b;
  font-size: 0.9rem;
}

.field input,
.field select,
.field textarea {
  width: 100%;
  border: 1px solid #becbc4;
  border-radius: 6px;
  background: #ffffff;
  color: #17201b;
  padding: 10px 12px;
}

.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.actions button,
.chat button {
  border: 0;
  border-radius: 6px;
  background: #123c2f;
  color: #ffffff;
  padding: 10px 12px;
  cursor: pointer;
}

.chat {
  display: grid;
  align-content: start;
  gap: 16px;
}

.answer {
  min-height: 220px;
  border: 1px solid #d6dfda;
  border-radius: 8px;
  background: #ffffff;
  padding: 18px;
  line-height: 1.5;
}

@media (max-width: 980px) {
  .shell {
    grid-template-columns: 1fr;
  }
}
```

Create `frontend/web/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app/App";

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 5: Verify scaffold passes**

Run:

```bash
npm --prefix frontend/web test -- --run src/app/App.test.tsx
npm --prefix frontend/web run lint
npm --prefix frontend/web run typecheck
npm --prefix frontend/web run build
```

Expected: test, typecheck and build pass.

- [ ] **Step 6: Remove keep file and commit**

Run:

```bash
git rm frontend/web/.gitkeep
git add frontend/web
git commit -m "feat: добавить каркас frontend web"
```

---

### Task 2: API Types and Clients

**Files:**
- Create: `frontend/web/src/app/types.ts`
- Create: `frontend/web/src/api/config.ts`
- Create: `frontend/web/src/api/errors.ts`
- Create: `frontend/web/src/api/chatStream.ts`
- Create: `frontend/web/src/api/news.ts`
- Create: `frontend/web/src/test/fixtures.ts`
- Create: `frontend/web/src/api/chatStream.test.ts`
- Create: `frontend/web/src/api/news.test.ts`

- [ ] **Step 1: Write failing SSE parser tests**

Create `frontend/web/src/test/fixtures.ts`:

```ts
import type { ChatResponse, NewsDocument, PreviewNewsResponse } from "../app/types";

export const sourceFixture: NewsDocument = {
  id: "news-1",
  title: "GDP grows",
  text: "GDP grew by 2 percent.",
  source: "demo",
  score: 0.75,
  published_at: null,
  metadata: { sector: "macro" },
};

export const chatResponseFixture: ChatResponse = {
  answer: "Рост ВВП обычно поддерживает рынок.",
  sources: [sourceFixture],
  impact_summaries: [
    {
      news_id: "news-1",
      model_name: "tfidf-logreg",
      impact: "positive",
      confidence: 0.82,
      explanation: "Рост ВВП обычно поддерживает рынок.",
    },
  ],
  analysis_model: "tfidf-logreg",
  metadata: {
    dialog_model_name: "template-dialog-generator",
    used_context_ids: ["news-1"],
  },
};

export const previewFixture: PreviewNewsResponse = {
  total_count: 1,
  documents: [
    {
      id: "news-1",
      title: "GDP grows",
      text: "GDP grew by 2 percent.",
      source: "demo",
      published_at: null,
      metadata: { row_number: 2 },
    },
  ],
};
```

Create `frontend/web/src/api/chatStream.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";

import { chatResponseFixture } from "../test/fixtures";
import { parseSsePayload, streamChat } from "./chatStream";

describe("parseSsePayload", () => {
  it("parses named SSE events with JSON data", () => {
    const events = parseSsePayload(
      [
        'event: chat_started',
        'data: {"question":"Что с ВВП?","analysis_model":"tfidf-logreg"}',
        '',
        'event: answer_completed',
        `data: ${JSON.stringify(chatResponseFixture)}`,
        '',
      ].join("\n"),
    );

    expect(events).toEqual([
      {
        event: "chat_started",
        data: { question: "Что с ВВП?", analysis_model: "tfidf-logreg" },
      },
      {
        event: "answer_completed",
        data: chatResponseFixture,
      },
    ]);
  });

  it("rejects malformed JSON payloads", () => {
    expect(() => parseSsePayload("event: error\ndata: {bad-json}\n\n")).toThrow(
      "Некорректный ответ stream API",
    );
  });
});

describe("streamChat", () => {
  it("posts the chat request and returns stream events", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('event: done\ndata: {"status":"ok"}\n\n', {
        status: 200,
        headers: { "content-type": "text/event-stream" },
      }),
    );

    const events = await streamChat(
      {
        question: "Что с ВВП?",
        analysis_model: "tfidf-logreg",
        limit: 5,
        source: null,
      },
      { baseUrl: "http://localhost:8000", fetcher: fetchMock },
    );

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/v1/chat/stream", {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question: "Что с ВВП?",
        analysis_model: "tfidf-logreg",
        limit: 5,
        source: null,
      }),
    });
    expect(events).toEqual([{ event: "done", data: { status: "ok" } }]);
  });
});
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
npm --prefix frontend/web test -- --run src/api/chatStream.test.ts
```

Expected: fail because `app/types.ts` and `api/chatStream.ts` do not exist.

- [ ] **Step 3: Implement shared types and chat stream client**

Create `frontend/web/src/app/types.ts`:

```ts
export type AnalysisModelName = "tfidf-logreg" | "embedding-logreg" | "tiny-transformer";
export type ImpactLabel = "positive" | "neutral" | "negative";

export type NewsDocument = {
  id: string;
  title: string;
  text: string;
  source: string;
  score?: number;
  published_at: string | null;
  metadata: Record<string, unknown>;
};

export type ImpactSummary = {
  news_id: string;
  model_name: AnalysisModelName;
  impact: ImpactLabel;
  confidence: number | null;
  explanation: string;
};

export type ChatRequest = {
  question: string;
  analysis_model: AnalysisModelName;
  limit: number;
  source: string | null;
};

export type ChatResponse = {
  answer: string;
  sources: NewsDocument[];
  impact_summaries: ImpactSummary[];
  analysis_model: AnalysisModelName;
  metadata: Record<string, unknown>;
};

export type ChatStreamEvent = {
  event: string;
  data: Record<string, unknown>;
};

export type PreviewNewsResponse = {
  documents: NewsDocument[];
  total_count: number;
};

export type IndexNewsDatasetResponse = {
  loaded_count: number;
  indexed_count: number;
  collection_name: string;
};
```

Create `frontend/web/src/api/errors.ts`:

```ts
export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export async function errorFromResponse(response: Response, fallback: string): Promise<ApiError> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.trim()) {
      return new ApiError(payload.detail);
    }
  } catch {
    return new ApiError(fallback);
  }
  return new ApiError(fallback);
}

export function connectionError(): ApiError {
  return new ApiError("Не удалось подключиться к сервису");
}
```

Create `frontend/web/src/api/config.ts`:

```ts
export const API_GATEWAY_URL =
  import.meta.env.VITE_API_GATEWAY_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export const NEWS_SERVICE_URL =
  import.meta.env.VITE_NEWS_SERVICE_URL?.replace(/\/$/, "") ?? "http://localhost:8004";
```

Create `frontend/web/src/api/chatStream.ts`:

```ts
import type { ChatRequest, ChatStreamEvent } from "../app/types";
import { API_GATEWAY_URL } from "./config";
import { ApiError, connectionError, errorFromResponse } from "./errors";

type StreamChatOptions = {
  baseUrl?: string;
  fetcher?: typeof fetch;
};

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/$/, "");
}

export function parseSsePayload(payload: string): ChatStreamEvent[] {
  return payload
    .split(/\n\n+/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) => {
      const eventLine = block.split("\n").find((line) => line.startsWith("event: "));
      const dataLine = block.split("\n").find((line) => line.startsWith("data: "));
      const event = eventLine?.replace("event: ", "").trim();
      const data = dataLine?.replace("data: ", "");

      if (!event || data === undefined) {
        throw new ApiError("Некорректный ответ stream API");
      }

      try {
        return { event, data: JSON.parse(data) as Record<string, unknown> };
      } catch (error) {
        throw new ApiError("Некорректный ответ stream API", { cause: error });
      }
    });
}

export async function streamChat(
  request: ChatRequest,
  options: StreamChatOptions = {},
): Promise<ChatStreamEvent[]> {
  const fetcher = options.fetcher ?? fetch;
  let response: Response;
  try {
    response = await fetcher(`${normalizeBaseUrl(options.baseUrl ?? API_GATEWAY_URL)}/api/v1/chat/stream`, {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });
  } catch (error) {
    throw connectionError();
  }

  if (!response.ok) {
    throw await errorFromResponse(response, "chat stream is unavailable");
  }

  const body = await response.text();
  return parseSsePayload(body);
}
```

- [ ] **Step 4: Write failing news client tests**

Create `frontend/web/src/api/news.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";

import { previewFixture } from "../test/fixtures";
import { indexNewsDataset, previewNews } from "./news";

describe("news api", () => {
  it("loads preview documents", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json(previewFixture));

    const response = await previewNews({ limit: 5 }, { baseUrl: "http://localhost:8004", fetcher: fetchMock });

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8004/api/v1/news/preview?limit=5");
    expect(response).toEqual(previewFixture);
  });

  it("indexes the local dataset", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json({
        loaded_count: 10,
        indexed_count: 10,
        collection_name: "economic_news",
      }),
    );

    const response = await indexNewsDataset(
      { limit: 10 },
      { baseUrl: "http://localhost:8004", fetcher: fetchMock },
    );

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8004/api/v1/news/index", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ limit: 10 }),
    });
    expect(response.indexed_count).toBe(10);
  });
});
```

- [ ] **Step 5: Run tests and verify they fail**

Run:

```bash
npm --prefix frontend/web test -- --run src/api/news.test.ts
```

Expected: fail because `api/news.ts` does not exist.

- [ ] **Step 6: Implement news clients**

Create `frontend/web/src/api/news.ts`:

```ts
import type { IndexNewsDatasetResponse, PreviewNewsResponse } from "../app/types";
import { NEWS_SERVICE_URL } from "./config";
import { connectionError, errorFromResponse } from "./errors";

type ApiOptions = {
  baseUrl?: string;
  fetcher?: typeof fetch;
};

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/$/, "");
}

export async function previewNews(
  request: { limit: number },
  options: ApiOptions = {},
): Promise<PreviewNewsResponse> {
  const fetcher = options.fetcher ?? fetch;
  const url = new URL(`${normalizeBaseUrl(options.baseUrl ?? NEWS_SERVICE_URL)}/api/v1/news/preview`);
  url.searchParams.set("limit", String(request.limit));

  let response: Response;
  try {
    response = await fetcher(url.toString());
  } catch {
    throw connectionError();
  }

  if (!response.ok) {
    throw await errorFromResponse(response, "news source is unavailable");
  }
  return (await response.json()) as PreviewNewsResponse;
}

export async function indexNewsDataset(
  request: { limit: number },
  options: ApiOptions = {},
): Promise<IndexNewsDatasetResponse> {
  const fetcher = options.fetcher ?? fetch;
  let response: Response;
  try {
    response = await fetcher(`${normalizeBaseUrl(options.baseUrl ?? NEWS_SERVICE_URL)}/api/v1/news/index`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
  } catch {
    throw connectionError();
  }

  if (!response.ok) {
    throw await errorFromResponse(response, "news indexing is unavailable");
  }
  return (await response.json()) as IndexNewsDatasetResponse;
}
```

- [ ] **Step 7: Verify API clients**

Run:

```bash
npm --prefix frontend/web test -- --run src/api/chatStream.test.ts src/api/news.test.ts
npm --prefix frontend/web run lint
npm --prefix frontend/web run typecheck
```

Expected: tests and typecheck pass.

- [ ] **Step 8: Commit**

Run:

```bash
git add frontend/web/src/app/types.ts frontend/web/src/api frontend/web/src/test
git commit -m "feat: добавить api клиенты frontend"
```

---

### Task 3: Chat Console Components and App State

**Files:**
- Modify: `frontend/web/src/app/App.tsx`
- Modify: `frontend/web/src/app/App.module.css`
- Modify: `frontend/web/src/app/App.test.tsx`
- Create: `frontend/web/src/components/ControlsPanel.tsx`
- Create: `frontend/web/src/components/ChatPanel.tsx`
- Create: `frontend/web/src/components/Timeline.tsx`
- Create: `frontend/web/src/components/SourcesPanel.tsx`
- Create: `frontend/web/src/components/NewsPreview.tsx`
- Create: `frontend/web/src/components/StatusMessage.tsx`

- [ ] **Step 1: Write failing App interaction tests**

Replace `frontend/web/src/app/App.test.tsx` with:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { chatResponseFixture, previewFixture } from "../test/fixtures";
import { App } from "./App";

function mockFetch() {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);

    if (url.includes("/api/v1/news/preview")) {
      return Response.json(previewFixture);
    }

    if (url.includes("/api/v1/news/index")) {
      return Response.json({
        loaded_count: 10,
        indexed_count: 10,
        collection_name: "economic_news",
      });
    }

    if (url.includes("/api/v1/chat/stream")) {
      return new Response(
        [
          'event: chat_started',
          'data: {"question":"Что с ВВП?","analysis_model":"embedding-logreg","limit":3,"source":null}',
          '',
          'event: sources_found',
          `data: ${JSON.stringify({ count: 1, sources: chatResponseFixture.sources })}`,
          '',
          'event: analysis_completed',
          `data: ${JSON.stringify({ count: 1, impact_summaries: chatResponseFixture.impact_summaries })}`,
          '',
          'event: answer_completed',
          `data: ${JSON.stringify(chatResponseFixture)}`,
          '',
          'event: done',
          'data: {"status":"ok"}',
          '',
        ].join("\n"),
        { status: 200, headers: { "content-type": "text/event-stream" } },
      );
    }

    return Response.json({ detail: "not found" }, { status: 404 });
  });
}

describe("App", () => {
  it("renders the chat console controls and empty state", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Economic News Dialog" })).toBeInTheDocument();
    expect(screen.getByLabelText("Модель анализа")).toBeInTheDocument();
    expect(screen.getByLabelText("Лимит источников")).toBeInTheDocument();
    expect(screen.getByLabelText("Источник")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Preview CSV" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Index CSV" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Вопрос" })).toBeInTheDocument();
    expect(screen.getByText("Ответ появится после отправки вопроса.")).toBeInTheDocument();
  });

  it("submits a real stream request shape and renders answer, timeline, sources and impacts", async () => {
    const fetchMock = mockFetch();
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<App />);
    await user.selectOptions(screen.getByLabelText("Модель анализа"), "embedding-logreg");
    await user.clear(screen.getByLabelText("Лимит источников"));
    await user.type(screen.getByLabelText("Лимит источников"), "3");
    await user.type(screen.getByRole("textbox", { name: "Вопрос" }), "Что с ВВП?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => {
      expect(screen.getByText("Рост ВВП обычно поддерживает рынок.")).toBeInTheDocument();
    });
    expect(screen.getByText("answer_completed")).toBeInTheDocument();
    expect(screen.getByText("GDP grows")).toBeInTheDocument();
    expect(screen.getByText("positive")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/chat/stream",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          question: "Что с ВВП?",
          analysis_model: "embedding-logreg",
          limit: 3,
          source: null,
        }),
      }),
    );
  });

  it("loads preview and indexes the dataset", async () => {
    vi.stubGlobal("fetch", mockFetch());
    const user = userEvent.setup();

    render(<App />);
    await user.click(screen.getByRole("button", { name: "Preview CSV" }));
    await waitFor(() => {
      expect(screen.getByText("Preview: 1 / 1")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Index CSV" }));
    await waitFor(() => {
      expect(screen.getByText("Indexed 10 of 10 into economic_news")).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
npm --prefix frontend/web test -- --run src/app/App.test.tsx
```

Expected: fail because the current App shell has no real interactions.

- [ ] **Step 3: Add focused presentational components**

Create `frontend/web/src/components/StatusMessage.tsx`:

```tsx
type StatusMessageProps = {
  title: string;
  detail?: string;
  tone?: "neutral" | "error" | "success";
};

export function StatusMessage({ title, detail, tone = "neutral" }: StatusMessageProps) {
  return (
    <div data-tone={tone}>
      <strong>{title}</strong>
      {detail ? <p>{detail}</p> : null}
    </div>
  );
}
```

Create `frontend/web/src/components/ControlsPanel.tsx`:

```tsx
import type { AnalysisModelName } from "../app/types";

type ControlsPanelProps = {
  analysisModel: AnalysisModelName;
  limit: number;
  source: string;
  isPreviewLoading: boolean;
  isIndexLoading: boolean;
  onAnalysisModelChange: (value: AnalysisModelName) => void;
  onLimitChange: (value: number) => void;
  onSourceChange: (value: string) => void;
  onPreview: () => void;
  onIndex: () => void;
};

const ANALYSIS_MODELS: AnalysisModelName[] = [
  "tfidf-logreg",
  "embedding-logreg",
  "tiny-transformer",
];

export function ControlsPanel({
  analysisModel,
  limit,
  source,
  isPreviewLoading,
  isIndexLoading,
  onAnalysisModelChange,
  onLimitChange,
  onSourceChange,
  onPreview,
  onIndex,
}: ControlsPanelProps) {
  return (
    <aside>
      <p>Local RAG pipeline</p>
      <h1>Economic News Dialog</h1>

      <label>
        <span>Модель анализа</span>
        <select
          aria-label="Модель анализа"
          value={analysisModel}
          onChange={(event) => onAnalysisModelChange(event.target.value as AnalysisModelName)}
        >
          {ANALYSIS_MODELS.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
      </label>

      <label>
        <span>Лимит источников</span>
        <input
          aria-label="Лимит источников"
          type="number"
          min={1}
          max={20}
          value={limit}
          onChange={(event) => onLimitChange(Number(event.target.value))}
        />
      </label>

      <label>
        <span>Источник</span>
        <input
          aria-label="Источник"
          value={source}
          placeholder="all sources"
          onChange={(event) => onSourceChange(event.target.value)}
        />
      </label>

      <button type="button" onClick={onPreview} disabled={isPreviewLoading}>
        {isPreviewLoading ? "Loading preview" : "Preview CSV"}
      </button>
      <button type="button" onClick={onIndex} disabled={isIndexLoading}>
        {isIndexLoading ? "Indexing" : "Index CSV"}
      </button>
    </aside>
  );
}
```

Create `frontend/web/src/components/ChatPanel.tsx`:

```tsx
type ChatPanelProps = {
  question: string;
  answer: string;
  isStreaming: boolean;
  error: string | null;
  onQuestionChange: (value: string) => void;
  onSubmit: () => void;
};

export function ChatPanel({
  question,
  answer,
  isStreaming,
  error,
  onQuestionChange,
  onSubmit,
}: ChatPanelProps) {
  return (
    <section>
      <label>
        <span>Вопрос</span>
        <textarea
          aria-label="Вопрос"
          rows={4}
          value={question}
          placeholder="Что означает рост ВВП для рынка?"
          onChange={(event) => onQuestionChange(event.target.value)}
        />
      </label>
      <button type="button" onClick={onSubmit} disabled={isStreaming || !question.trim()}>
        {isStreaming ? "Streaming" : "Ask"}
      </button>
      {error ? <p role="alert">{error}</p> : null}
      <article>{answer || "Ответ появится после отправки вопроса."}</article>
    </section>
  );
}
```

Create `frontend/web/src/components/Timeline.tsx`:

```tsx
import type { ChatStreamEvent } from "../app/types";

type TimelineProps = {
  events: ChatStreamEvent[];
};

export function Timeline({ events }: TimelineProps) {
  return (
    <section aria-label="Pipeline timeline">
      <h2>Timeline</h2>
      {events.length === 0 ? (
        <p>События pipeline появятся во время ответа.</p>
      ) : (
        <ol>
          {events.map((event, index) => (
            <li key={`${event.event}-${index}`}>{event.event}</li>
          ))}
        </ol>
      )}
    </section>
  );
}
```

Create `frontend/web/src/components/SourcesPanel.tsx`:

```tsx
import type { ImpactSummary, NewsDocument } from "../app/types";

type SourcesPanelProps = {
  sources: NewsDocument[];
  impactSummaries: ImpactSummary[];
};

function impactForSource(source: NewsDocument, impactSummaries: ImpactSummary[]) {
  return impactSummaries.find((summary) => summary.news_id === source.id);
}

export function SourcesPanel({ sources, impactSummaries }: SourcesPanelProps) {
  return (
    <aside>
      <h2>Sources</h2>
      {sources.length === 0 ? (
        <p>Источники появятся после ответа.</p>
      ) : (
        <div>
          {sources.map((source) => {
            const impact = impactForSource(source, impactSummaries);
            return (
              <article key={source.id}>
                <h3>{source.title}</h3>
                <p>{source.source}</p>
                {typeof source.score === "number" ? <p>score {source.score.toFixed(2)}</p> : null}
                {impact ? (
                  <section>
                    <strong>{impact.impact}</strong>
                    <p>{impact.explanation}</p>
                  </section>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </aside>
  );
}
```

Create `frontend/web/src/components/NewsPreview.tsx`:

```tsx
import type { IndexNewsDatasetResponse, PreviewNewsResponse } from "../app/types";

type NewsPreviewProps = {
  preview: PreviewNewsResponse | null;
  indexResult: IndexNewsDatasetResponse | null;
};

export function NewsPreview({ preview, indexResult }: NewsPreviewProps) {
  return (
    <section>
      <h2>Dataset</h2>
      {preview ? <p>Preview: {preview.documents.length} / {preview.total_count}</p> : <p>Preview is empty.</p>}
      {preview?.documents.map((document) => (
        <article key={document.id}>
          <h3>{document.title}</h3>
          <p>{document.source}</p>
        </article>
      ))}
      {indexResult ? (
        <p>
          Indexed {indexResult.indexed_count} of {indexResult.loaded_count} into{" "}
          {indexResult.collection_name}
        </p>
      ) : null}
    </section>
  );
}
```

- [ ] **Step 4: Wire App state to real API clients**

Replace `frontend/web/src/app/App.tsx` with:

```tsx
import { useState } from "react";

import { streamChat } from "../api/chatStream";
import { indexNewsDataset, previewNews } from "../api/news";
import { ChatPanel } from "../components/ChatPanel";
import { ControlsPanel } from "../components/ControlsPanel";
import { NewsPreview } from "../components/NewsPreview";
import { SourcesPanel } from "../components/SourcesPanel";
import { Timeline } from "../components/Timeline";
import type {
  AnalysisModelName,
  ChatResponse,
  ChatStreamEvent,
  ImpactSummary,
  IndexNewsDatasetResponse,
  NewsDocument,
  PreviewNewsResponse,
} from "./types";
import styles from "./App.module.css";

function messageFromError(error: unknown): string {
  return error instanceof Error ? error.message : "Не удалось выполнить действие";
}

function clampLimit(value: number): number {
  if (!Number.isFinite(value)) {
    return 1;
  }
  return Math.min(20, Math.max(1, value));
}

function isChatResponse(data: Record<string, unknown>): data is ChatResponse {
  return typeof data.answer === "string" && Array.isArray(data.sources);
}

export function App() {
  const [analysisModel, setAnalysisModel] = useState<AnalysisModelName>("tfidf-logreg");
  const [limit, setLimit] = useState(5);
  const [source, setSource] = useState("");
  const [question, setQuestion] = useState("");
  const [events, setEvents] = useState<ChatStreamEvent[]>([]);
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<NewsDocument[]>([]);
  const [impactSummaries, setImpactSummaries] = useState<ImpactSummary[]>([]);
  const [preview, setPreview] = useState<PreviewNewsResponse | null>(null);
  const [indexResult, setIndexResult] = useState<IndexNewsDatasetResponse | null>(null);
  const [isStreaming, setStreaming] = useState(false);
  const [isPreviewLoading, setPreviewLoading] = useState(false);
  const [isIndexLoading, setIndexLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setStreaming(true);
    setError(null);
    setEvents([]);
    setAnswer("");
    setSources([]);
    setImpactSummaries([]);
    try {
      const streamEvents = await streamChat({
        question,
        analysis_model: analysisModel,
        limit,
        source: source.trim() || null,
      });
      setEvents(streamEvents);
      const errorEvent = streamEvents.find((event) => event.event === "error");
      if (errorEvent) {
        setError(String(errorEvent.data.detail ?? "chat stream is unavailable"));
      }
      const answerEvent = streamEvents.findLast((event) => event.event === "answer_completed");
      if (answerEvent && isChatResponse(answerEvent.data)) {
        setAnswer(answerEvent.data.answer);
        setSources(answerEvent.data.sources);
        setImpactSummaries(answerEvent.data.impact_summaries);
      }
    } catch (streamError) {
      setError(messageFromError(streamError));
    } finally {
      setStreaming(false);
    }
  }

  async function handlePreview() {
    setPreviewLoading(true);
    setError(null);
    try {
      setPreview(await previewNews({ limit: 5 }));
    } catch (previewError) {
      setError(messageFromError(previewError));
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleIndex() {
    setIndexLoading(true);
    setError(null);
    try {
      setIndexResult(await indexNewsDataset({ limit: 100 }));
    } catch (indexError) {
      setError(messageFromError(indexError));
    } finally {
      setIndexLoading(false);
    }
  }

  return (
    <main className={styles.shell}>
      <div className={styles.controls}>
        <ControlsPanel
          analysisModel={analysisModel}
          limit={limit}
          source={source}
          isPreviewLoading={isPreviewLoading}
          isIndexLoading={isIndexLoading}
          onAnalysisModelChange={setAnalysisModel}
          onLimitChange={(value) => setLimit(clampLimit(value))}
          onSourceChange={setSource}
          onPreview={handlePreview}
          onIndex={handleIndex}
        />
        <NewsPreview preview={preview} indexResult={indexResult} />
      </div>
      <div className={styles.chat}>
        <ChatPanel
          question={question}
          answer={answer}
          isStreaming={isStreaming}
          error={error}
          onQuestionChange={setQuestion}
          onSubmit={handleSubmit}
        />
        <Timeline events={events} />
      </div>
      <div className={styles.sources}>
        <SourcesPanel sources={sources} impactSummaries={impactSummaries} />
      </div>
    </main>
  );
}
```

- [ ] **Step 5: Replace CSS with final responsive console styling**

Replace `frontend/web/src/app/App.module.css` with CSS that keeps the same class names:

```css
:global(*) {
  box-sizing: border-box;
}

:global(body) {
  margin: 0;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #eef2ef;
  color: #17201b;
}

:global(button),
:global(input),
:global(select),
:global(textarea) {
  font: inherit;
}

:global(button) {
  border: 0;
  border-radius: 6px;
  background: #123c2f;
  color: #ffffff;
  padding: 10px 12px;
  cursor: pointer;
}

:global(button:disabled) {
  cursor: not-allowed;
  opacity: 0.62;
}

:global(label) {
  display: grid;
  gap: 6px;
  margin-bottom: 14px;
  color: #34443b;
  font-size: 0.9rem;
}

:global(input),
:global(select),
:global(textarea) {
  width: 100%;
  border: 1px solid #becbc4;
  border-radius: 6px;
  background: #ffffff;
  color: #17201b;
  padding: 10px 12px;
}

:global(article) {
  border: 1px solid #d6dfda;
  border-radius: 8px;
  background: #ffffff;
  padding: 14px;
  margin-bottom: 10px;
}

:global(h1),
:global(h2),
:global(h3),
:global(p) {
  letter-spacing: 0;
}

.shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(420px, 1fr) minmax(300px, 380px);
  gap: 1px;
  background: #cfd8d3;
}

.controls,
.chat,
.sources {
  background: #f8faf8;
  padding: 24px;
  min-width: 0;
}

.controls {
  display: grid;
  align-content: start;
  gap: 18px;
}

.chat {
  display: grid;
  align-content: start;
  gap: 18px;
}

.sources {
  overflow: auto;
}

@media (max-width: 1060px) {
  .shell {
    grid-template-columns: 1fr;
  }

  .controls,
  .chat,
  .sources {
    padding: 18px;
  }
}
```

- [ ] **Step 6: Verify App tests pass**

Run:

```bash
npm --prefix frontend/web test -- --run src/app/App.test.tsx
npm --prefix frontend/web run lint
npm --prefix frontend/web run typecheck
npm --prefix frontend/web run build
```

Expected: all pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add frontend/web/src
git commit -m "feat: добавить frontend chat console"
```

---

### Task 4: Frontend Infrastructure and Documentation

**Files:**
- Create: `deploy/docker/frontend-web.Dockerfile`
- Create: `deploy/docker/frontend-web.nginx.conf`
- Modify: `deploy/compose.yaml`
- Modify: `justfile`
- Modify: `README.md`
- Modify: `.env.example`

- [ ] **Step 1: Add Dockerfile and nginx config**

Create `deploy/docker/frontend-web.nginx.conf`:

```nginx
server {
  listen 80;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;

  location / {
    try_files $uri $uri/ /index.html;
  }
}
```

Create `deploy/docker/frontend-web.Dockerfile`:

```dockerfile
FROM node:22-alpine AS build

WORKDIR /app

ARG VITE_API_GATEWAY_URL=http://localhost:8000
ARG VITE_NEWS_SERVICE_URL=http://localhost:8004
ENV VITE_API_GATEWAY_URL=${VITE_API_GATEWAY_URL}
ENV VITE_NEWS_SERVICE_URL=${VITE_NEWS_SERVICE_URL}

COPY frontend/web/package*.json ./frontend/web/
RUN npm --prefix frontend/web ci

COPY frontend/web ./frontend/web
RUN npm --prefix frontend/web run build

FROM nginx:1.27-alpine AS runtime

COPY deploy/docker/frontend-web.nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/web/dist /usr/share/nginx/html
```

- [ ] **Step 2: Add compose service and env examples**

Modify `.env.example` by appending:

```env
VITE_API_GATEWAY_URL=http://localhost:8000
VITE_NEWS_SERVICE_URL=http://localhost:8004
```

Modify `deploy/compose.yaml` by adding:

```yaml
  frontend-web:
    build:
      context: ..
      dockerfile: deploy/docker/frontend-web.Dockerfile
      args:
        VITE_API_GATEWAY_URL: "${VITE_API_GATEWAY_URL:-http://localhost:8000}"
        VITE_NEWS_SERVICE_URL: "${VITE_NEWS_SERVICE_URL:-http://localhost:8004}"
    ports:
      - "5173:80"
    depends_on:
      - api-gateway
      - news-service
```

- [ ] **Step 3: Add Justfile commands**

Append to `justfile`:

```just
web-dev:
    npm --prefix frontend/web run dev -- --host 0.0.0.0 --port 5173

web-test:
    npm --prefix frontend/web test -- --run

web-build:
    npm --prefix frontend/web run build
```

- [ ] **Step 4: Update README**

Add section after `News Service ingestion`:

````markdown
## Frontend Chat Console

The React UI is a real API client for the local backend.

Local development:

```bash
npm --prefix frontend/web install
VITE_API_GATEWAY_URL=http://localhost:8000 \
VITE_NEWS_SERVICE_URL=http://localhost:8004 \
  npm --prefix frontend/web run dev -- --host 0.0.0.0 --port 5173
```

Open:

```text
http://localhost:5173
```

Expected backend services:

- `api-gateway` on `http://localhost:8000`;
- `news-service` on `http://localhost:8004`.

Checks:

```bash
npm --prefix frontend/web test -- --run
npm --prefix frontend/web run lint
npm --prefix frontend/web run typecheck
npm --prefix frontend/web run build
```
````

- [ ] **Step 5: Run frontend checks**

Run:

```bash
npm --prefix frontend/web test -- --run
npm --prefix frontend/web run typecheck
npm --prefix frontend/web run build
docker compose -f deploy/compose.yaml config
```

Expected: all pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add .env.example README.md justfile deploy/compose.yaml deploy/docker/frontend-web.Dockerfile deploy/docker/frontend-web.nginx.conf
git commit -m "chore: подключить frontend web"
```

---

### Task 5: Final Verification, Browser Check and PR

**Files:**
- Modify only if verification reveals a defect.

- [ ] **Step 1: Run full repository checks**

Run:

```bash
uv run ruff check apps packages research
uv run ty check apps packages research
uv run pytest packages apps research/tests -q -W error
npm --prefix frontend/web test -- --run
npm --prefix frontend/web run lint
npm --prefix frontend/web run typecheck
npm --prefix frontend/web run build
docker compose -f deploy/compose.yaml config
```

Expected: all pass.

- [ ] **Step 2: Start the frontend dev server**

Run:

```bash
npm --prefix frontend/web run dev -- --host 0.0.0.0 --port 5173
```

Expected: Vite serves the UI at `http://localhost:5173`.

- [ ] **Step 3: Browser smoke test**

Use the in-app browser or Playwright to open:

```text
http://localhost:5173
```

Verify:

- heading `Economic News Dialog` is visible;
- model selector is visible;
- question input is visible;
- preview/index buttons are visible;
- layout does not overlap at desktop width.

If backend services are not running, verify that clicking actions shows a sanitized connection error rather than crashing.

- [ ] **Step 4: Try Docker build if Docker daemon is available**

Run:

```bash
docker compose -f deploy/compose.yaml build frontend-web
```

Expected: build succeeds. If Docker daemon is unavailable, record the daemon error and do not claim Docker build passed.

- [ ] **Step 5: Final branch review**

Request a final review for `origin/dev..HEAD` with this checklist:

- UI is chat-first and not a landing page;
- UI uses real backend API calls only;
- stream parser handles named SSE JSON events;
- `analysis_model`, `limit` and `source` are sent in chat request;
- preview/index buttons call `news-service`;
- errors are sanitized;
- frontend tests cover API clients and app interactions;
- compose/README/Justfile are wired.

Expected: reviewer returns `PASS` or only non-blocking comments.

- [ ] **Step 6: Push and create PR**

Run:

```bash
git push -u origin feature/frontend-chat-console
gh pr create --base dev --head feature/frontend-chat-console --title "feat: добавить frontend chat console" --body "<summary and checks>"
```

Expected: PR is created against `dev`.

---

## Plan Self-Review

Spec coverage:

- Vite React TypeScript CSS Modules: Tasks 1 and 3.
- Real API only: Tasks 2 and 3.
- Chat stream through `POST /api/v1/chat/stream`: Task 2 client and Task 3 UI.
- News preview/index: Task 2 clients and Task 3 controls.
- Model switcher: Task 3 controls and tests.
- Error states: Task 2 client errors and Task 3 app error rendering.
- Docker Compose, Dockerfile, README and Justfile: Task 4.
- Verification and browser check: Task 5.

Placeholder scan:

- No TBD/TODO/deferred implementation markers are used.
- Each code-changing step includes concrete file content or exact snippets.

Type consistency:

- `AnalysisModelName` values match backend contract names used in tests.
- Chat stream event names match backend `ChatStreamUseCase`.
- `NewsDocument`, `ImpactSummary`, `PreviewNewsResponse` and `IndexNewsDatasetResponse` match backend JSON shapes.

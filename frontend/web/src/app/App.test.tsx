import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { chatResponseFixture, previewFixture } from "../test/fixtures";
import { App } from "./App";

function mockFetch() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);

    if (url.includes("/api/v1/news/datasets/upload")) {
      return Response.json({
        dataset_id: "macro",
        filename: "macro.csv",
        size_bytes: 32,
        uploaded_at: "2026-05-08T10:00:00Z",
      });
    }

    if (url.includes("/api/v1/news/datasets/macro/activate")) {
      return Response.json({
        dataset_id: "macro",
        filename: "macro.csv",
        activated_at: "2026-05-08T10:01:00Z",
      });
    }

    if (url.includes("/api/v1/news/datasets/active")) {
      return Response.json(null);
    }

    if (url.includes("/api/v1/news/datasets")) {
      return Response.json({
        datasets: [
          {
            dataset_id: "macro",
            filename: "macro.csv",
            size_bytes: 32,
            uploaded_at: "2026-05-08T10:00:00Z",
          },
        ],
      });
    }

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
          "event: chat_started",
          'data: {"question":"Что с ВВП?","analysis_model":"embedding-logreg","limit":3,"source":null}',
          "",
          "event: sources_found",
          `data: ${JSON.stringify({ count: 1, sources: chatResponseFixture.sources })}`,
          "",
          "event: analysis_completed",
          `data: ${JSON.stringify({ count: 1, impact_summaries: chatResponseFixture.impact_summaries })}`,
          "",
          "event: answer_completed",
          `data: ${JSON.stringify(chatResponseFixture)}`,
          "",
          "event: done",
          'data: {"status":"ok"}',
          "",
        ].join("\n"),
        { status: 200, headers: { "content-type": "text/event-stream" } },
      );
    }

    return Response.json({ detail: "not found" }, { status: 404 });
  });
}

function mockStreamErrorFetch() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);

    if (url.includes("/api/v1/chat/stream")) {
      return new Response(
        ["event: error", 'data: {"detail":"retrieval service is unavailable"}', ""].join("\n"),
        { status: 200, headers: { "content-type": "text/event-stream" } },
      );
    }

    return Response.json({ detail: "not found" }, { status: 404 });
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("renders the chat console controls and empty state", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", {
        name: "Диалоговая система анализа экономических новостей",
      }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Модель анализа")).toBeInTheDocument();
    expect(screen.getByLabelText("Лимит источников")).toBeInTheDocument();
    expect(screen.getByLabelText("Источник")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Предпросмотр CSV" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Индексировать CSV" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Вопрос" })).toBeInTheDocument();
    expect(screen.getByText("Ответ появится после отправки вопроса.")).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Источники анализа" })).toBeInTheDocument();
    expect(screen.getByText("Источники появятся после ответа.")).toBeInTheDocument();
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
    await user.click(screen.getByRole("button", { name: "Спросить" }));

    await waitFor(() => {
      expect(screen.getByText("Рост ВВП обычно поддерживает рынок.")).toBeInTheDocument();
    });
    expect(screen.getByText("ответ сформирован")).toBeInTheDocument();
    expect(screen.getByText("ВВП вырос")).toBeInTheDocument();
    expect(screen.getByText("позитивное")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api-gateway/api/v1/chat/stream",
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

    await user.click(screen.getByRole("button", { name: "Предпросмотр CSV" }));
    await waitFor(() => {
      expect(screen.getByText("Предпросмотр: 1 / 1")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Индексировать CSV" }));
    await waitFor(() => {
      expect(screen.getByText("Проиндексировано 10 из 10 в economic_news")).toBeInTheDocument();
    });
  });

  it("uploads a csv dataset and displays it as active", async () => {
    const fetchMock = mockFetch();
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<App />);

    await user.upload(
      screen.getByLabelText("CSV датасет"),
      new File(["id,title\n1,GDP"], "macro.csv", { type: "text/csv" }),
    );

    await waitFor(() => {
      expect(screen.getByText("Активен: macro.csv")).toBeInTheDocument();
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/news-service/api/v1/news/datasets/upload",
      expect.objectContaining({ method: "POST", body: expect.any(FormData) }),
    );
    expect(fetchMock).toHaveBeenCalledWith("/news-service/api/v1/news/datasets/macro/activate", {
      method: "POST",
    });
  });

  it("renders stream error events as an alert", async () => {
    vi.stubGlobal("fetch", mockStreamErrorFetch());
    const user = userEvent.setup();

    render(<App />);

    await user.type(screen.getByRole("textbox", { name: "Вопрос" }), "Что с ВВП?");
    await user.click(screen.getByRole("button", { name: "Спросить" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Не удалось завершить потоковый ответ");
    });
    expect(screen.getByText("ошибка")).toBeInTheDocument();
  });
});

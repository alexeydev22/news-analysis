import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { chatResponseFixture, mlReportFixture, previewFixture, topicForecastFixture } from "../test/fixtures";
import { App } from "./App";

function deferredResponse() {
  let resolve!: (response: Response) => void;
  const promise = new Promise<Response>((resolvePromise) => {
    resolve = resolvePromise;
  });

  return { promise, resolve };
}

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

    if (url.includes("/api/v1/ml-report/latest")) {
      return new Response(null, { status: 204 });
    }

    if (url.includes("/api/v1/ml-report/jobs/job-1")) {
      return Response.json({
        job_id: "job-1",
        status: "succeeded",
        message: "ready",
        report_path: "reports/ml.json",
      });
    }

    if (url.includes("/api/v1/ml-report/jobs")) {
      return Response.json({ job_id: "job-1", status: "queued" });
    }

    if (url.includes("/api/v1/topic-forecast/latest")) {
      return new Response(null, { status: 204 });
    }

    if (url.includes("/api/v1/topic-forecast/jobs/topic-job-1")) {
      return Response.json({
        job_id: "topic-job-1",
        status: "succeeded",
        message: "ready",
        report_path: "reports/topic-forecast/latest.json",
      });
    }

    if (url.includes("/api/v1/topic-forecast/jobs")) {
      return Response.json({ job_id: "topic-job-1", status: "queued" });
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
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("renders the chat console controls and empty state", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", {
        name: "Аналитика экономических новостей",
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Чат" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Данные" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ML-отчет" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Прогноз" })).toBeInTheDocument();
    expect(screen.getByLabelText("Модель анализа")).toBeInTheDocument();
    expect(screen.getByLabelText("Лимит источников")).toBeInTheDocument();
    expect(screen.getByLabelText("Источник")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Вопрос" })).toBeInTheDocument();
    expect(screen.getByText("Ответ появится после отправки вопроса.")).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Источники анализа" })).toBeInTheDocument();
    expect(screen.getByText("Источники появятся после ответа.")).toBeInTheDocument();
  });

  it("switches between analytics sections", async () => {
    vi.stubGlobal("fetch", mockFetch());
    const user = userEvent.setup();

    render(<App />);

    await user.click(screen.getByRole("button", { name: "Данные" }));
    expect(screen.getByRole("button", { name: "Данные" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { name: "Датасет и индекс" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Предпросмотр CSV" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "ML-отчет" }));
    expect(screen.getByRole("heading", { name: "ML-отчет" })).toBeInTheDocument();
    expect(screen.getByText("Отчет еще не сформирован")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Прогноз" }));
    expect(screen.getByRole("heading", { name: "Прогноз по темам" })).toBeInTheDocument();
    expect(screen.getByText("Прогноз еще не сформирован")).toBeInTheDocument();
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
    expect(screen.queryByText("ВВП вырос на 2 процента.")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Показать полный текст новости ВВП вырос" }));
    expect(screen.getByText("ВВП вырос на 2 процента.")).toBeInTheDocument();
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

    await user.click(screen.getByRole("button", { name: "Данные" }));
    await user.click(screen.getByRole("button", { name: "Предпросмотр CSV" }));
    await waitFor(() => {
      expect(screen.getByText("Предпросмотр: 1 / 1")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "Показать полный текст новости ВВП вырос" }));
    expect(screen.getByText("ВВП вырос на 2 процента.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Индексировать CSV" }));
    await waitFor(() => {
      expect(screen.getByText("Проиндексировано 10 из 10 в economic_news")).toBeInTheDocument();
    });
  });

  it("starts an ml report job and renders the latest report", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/api/v1/news/datasets/active")) {
        return Response.json(null);
      }

      if (url.includes("/api/v1/news/datasets")) {
        return Response.json({ datasets: [] });
      }

      if (url.includes("/api/v1/ml-report/latest")) {
        return Response.json(mlReportFixture);
      }

      if (url.includes("/api/v1/ml-report/jobs/job-1")) {
        return Response.json({
          job_id: "job-1",
          status: "succeeded",
          message: "ready",
          report_path: "reports/ml.json",
        });
      }

      if (url.includes("/api/v1/ml-report/jobs")) {
        return Response.json({ job_id: "job-1", status: "succeeded" });
      }

      return Response.json({ detail: "not found" }, { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<App />);

    await user.click(screen.getByRole("button", { name: "ML-отчет" }));
    await user.click(screen.getByRole("button", { name: "Сформировать ML-отчет" }));
    expect(fetchMock).toHaveBeenCalledWith(
      "/analysis-service/api/v1/ml-report/jobs",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({}),
      }),
    );

    await waitFor(() => {
      expect(screen.getByText("Лучшая модель: tfidf-logreg")).toBeInTheDocument();
    });
    expect(screen.getByText("Строк в датасете: 120")).toBeInTheDocument();
    expect(screen.getByText("ввп")).toBeInTheDocument();
    expect(screen.getByText("0.900")).toBeInTheDocument();
  });

  it("starts a topic forecast job and renders the latest forecast", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/api/v1/news/datasets/active")) {
        return Response.json(null);
      }

      if (url.includes("/api/v1/news/datasets")) {
        return Response.json({ datasets: [] });
      }

      if (url.includes("/api/v1/ml-report/latest")) {
        return new Response(null, { status: 204 });
      }

      if (url.includes("/api/v1/topic-forecast/latest")) {
        return Response.json(topicForecastFixture);
      }

      if (url.includes("/api/v1/topic-forecast/jobs/topic-job-1")) {
        return Response.json({
          job_id: "topic-job-1",
          status: "succeeded",
          message: "ready",
          report_path: "reports/topic-forecast/latest.json",
        });
      }

      if (url.includes("/api/v1/topic-forecast/jobs")) {
        return Response.json({ job_id: "topic-job-1", status: "succeeded" });
      }

      return Response.json({ detail: "not found" }, { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<App />);

    await user.click(screen.getByRole("button", { name: "Прогноз" }));
    await user.click(screen.getByRole("button", { name: "Сформировать прогноз по темам" }));
    expect(fetchMock).toHaveBeenCalledWith(
      "/analysis-service/api/v1/topic-forecast/jobs",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({}),
      }),
    );

    await waitFor(() => {
      expect(screen.getByText("Рост ВВП")).toBeInTheDocument();
    });
    expect(screen.getByText("Сформировано: 2026-05-10T10:00:00Z")).toBeInTheDocument();
    expect(screen.getByText("Документов: 3")).toBeInTheDocument();
    expect(screen.getByText("Модель: tfidf-logreg")).toBeInTheDocument();
    expect(screen.getByText("Общее влияние: позитивное")).toBeInTheDocument();
    expect(screen.getByText("Уверенность: 0.800")).toBeInTheDocument();
    expect(screen.getByText("Позитивных: 2")).toBeInTheDocument();
    expect(screen.getByText("Нейтральных: 1")).toBeInTheDocument();
    expect(screen.getByText("Негативных: 0")).toBeInTheDocument();
    expect(screen.getByText("Рост ВВП поддерживает ожидания.")).toBeInTheDocument();
    expect(screen.getByText("Прогноз зависит от полноты набора новостей.")).toBeInTheDocument();
    expect(screen.getByText("ВВП вырос")).toBeInTheDocument();
    expect(screen.getByText("Демо · позитивное · 0.92")).toBeInTheDocument();
  });

  it("uploads a csv dataset and displays it as active", async () => {
    const fetchMock = mockFetch();
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<App />);

    await user.click(screen.getByRole("button", { name: "Данные" }));
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

  it("renders a disabled dataset placeholder instead of selectable demo option", async () => {
    vi.stubGlobal("fetch", mockFetch());
    const user = userEvent.setup();

    render(<App />);

    await user.click(screen.getByRole("button", { name: "Данные" }));
    const select = await screen.findByLabelText("Загруженные датасеты");
    expect(select).toHaveValue("");
    expect(screen.queryByRole("option", { name: "demo CSV" })).not.toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Выберите датасет" })).toBeDisabled();
  });

  it("keeps uploaded active dataset when stale initial refresh resolves later", async () => {
    const initialDatasets = deferredResponse();
    const initialActive = deferredResponse();
    let listCalls = 0;
    let activeCalls = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
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
        activeCalls += 1;
        return activeCalls === 1 ? initialActive.promise : Response.json(null);
      }

      if (url.includes("/api/v1/news/datasets")) {
        listCalls += 1;
        return listCalls === 1
          ? initialDatasets.promise
          : Response.json({
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

      return Response.json({ detail: "not found" }, { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<App />);

    await user.click(screen.getByRole("button", { name: "Данные" }));
    await user.upload(
      screen.getByLabelText("CSV датасет"),
      new File(["id,title\n1,GDP"], "macro.csv", { type: "text/csv" }),
    );
    await waitFor(() => {
      expect(screen.getByText("Активен: macro.csv")).toBeInTheDocument();
    });

    await act(async () => {
      initialDatasets.resolve(Response.json({ datasets: [] }));
      initialActive.resolve(Response.json(null));
      await Promise.resolve();
    });

    expect(screen.getByText("Активен: macro.csv")).toBeInTheDocument();
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

import { describe, expect, it, vi } from "vitest";

import { chatResponseFixture } from "../test/fixtures";
import { parseSsePayload, streamChat } from "./chatStream";

describe("parseSsePayload", () => {
  it("parses named SSE events with JSON data", () => {
    const events = parseSsePayload(
      [
        "event: chat_started",
        'data: {"question":"Что с ВВП?","analysis_model":"tfidf-logreg"}',
        "",
        "event: answer_completed",
        `data: ${JSON.stringify(chatResponseFixture)}`,
        "",
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

  it("emits events as soon as stream chunks complete an SSE block", async () => {
    const encoder = new TextEncoder();
    const receivedEvents: string[] = [];
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('event: chat_started\ndata: {"status":"started"}\n\n'));
        controller.enqueue(encoder.encode('event: done\ndata: {"status":"ok"}\n\n'));
        controller.close();
      },
    });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(stream, {
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
      {
        baseUrl: "http://localhost:8000",
        fetcher: fetchMock,
        onEvent: (event) => {
          receivedEvents.push(event.event);
        },
      },
    );

    expect(receivedEvents).toEqual(["chat_started", "done"]);
    expect(events).toEqual([
      { event: "chat_started", data: { status: "started" } },
      { event: "done", data: { status: "ok" } },
    ]);
  });

  it("normalizes interrupted stream body errors", async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.error(new Error("network lost"));
      },
    });
    const fetchMock = vi.fn().mockResolvedValue(new Response(stream, { status: 200 }));

    await expect(
      streamChat(
        {
          question: "Что с ВВП?",
          analysis_model: "tfidf-logreg",
          limit: 5,
          source: null,
        },
        { baseUrl: "http://localhost:8000", fetcher: fetchMock },
      ),
    ).rejects.toThrow("Не удалось подключиться к сервису");
  });
});

import type { ChatRequest, ChatStreamEvent } from "../app/types";
import { API_GATEWAY_URL } from "./config";
import { ApiError, connectionError, errorFromResponse } from "./errors";

type StreamChatOptions = {
  baseUrl?: string;
  fetcher?: typeof fetch;
  onEvent?: (event: ChatStreamEvent) => void;
};

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/$/, "");
}

function parseSseBlock(block: string): ChatStreamEvent {
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
}

export function parseSsePayload(payload: string): ChatStreamEvent[] {
  return payload
    .split(/\n\n+/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map(parseSseBlock);
}

function extractCompleteBlocks(buffer: string): { blocks: string[]; rest: string } {
  const blocks: string[] = [];
  let rest = buffer;
  let boundaryIndex = rest.search(/\n\n+/);

  while (boundaryIndex !== -1) {
    blocks.push(rest.slice(0, boundaryIndex));
    rest = rest.slice(boundaryIndex).replace(/^\n\n+/, "");
    boundaryIndex = rest.search(/\n\n+/);
  }

  return { blocks, rest };
}

async function readStreamEvents(
  response: Response,
  onEvent?: (event: ChatStreamEvent) => void,
): Promise<ChatStreamEvent[]> {
  if (!response.body) {
    return parseSsePayload(await response.text());
  }

  const events: ChatStreamEvent[] = [];
  const decoder = new TextDecoder();
  const reader = response.body.getReader();
  let buffer = "";

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const { blocks, rest } = extractCompleteBlocks(buffer);
      buffer = rest;

      for (const block of blocks) {
        const event = parseSseBlock(block.trim());
        events.push(event);
        onEvent?.(event);
      }
    }

    buffer += decoder.decode();
    if (buffer.trim()) {
      const event = parseSseBlock(buffer.trim());
      events.push(event);
      onEvent?.(event);
    }
  } catch {
    throw connectionError();
  }

  return events;
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
  } catch {
    throw connectionError();
  }

  if (!response.ok) {
    throw await errorFromResponse(response, "Не удалось получить потоковый ответ");
  }

  return readStreamEvents(response, options.onEvent);
}

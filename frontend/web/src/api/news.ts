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
  const params = new URLSearchParams({ limit: String(request.limit) });
  const url = `${normalizeBaseUrl(options.baseUrl ?? NEWS_SERVICE_URL)}/api/v1/news/preview?${params}`;

  let response: Response;
  try {
    response = await fetcher(url);
  } catch {
    throw connectionError();
  }

  if (!response.ok) {
    throw await errorFromResponse(response, "Не удалось загрузить предпросмотр новостей");
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
    throw await errorFromResponse(response, "Не удалось индексировать набор новостей");
  }

  return (await response.json()) as IndexNewsDatasetResponse;
}

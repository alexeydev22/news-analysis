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

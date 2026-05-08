import type {
  ActiveDataset,
  DatasetListResponse,
  IndexNewsDatasetResponse,
  PreviewNewsResponse,
  UploadedDataset,
} from "../app/types";
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

export async function uploadDataset(file: File, options: ApiOptions = {}): Promise<UploadedDataset> {
  const fetcher = options.fetcher ?? fetch;
  const body = new FormData();
  body.append("file", file);

  let response: Response;
  try {
    response = await fetcher(`${normalizeBaseUrl(options.baseUrl ?? NEWS_SERVICE_URL)}/api/v1/news/datasets/upload`, {
      method: "POST",
      body,
    });
  } catch {
    throw connectionError();
  }

  if (!response.ok) {
    throw await errorFromResponse(response, "Не удалось загрузить CSV датасет");
  }

  return (await response.json()) as UploadedDataset;
}

export async function listDatasets(options: ApiOptions = {}): Promise<DatasetListResponse> {
  const fetcher = options.fetcher ?? fetch;

  let response: Response;
  try {
    response = await fetcher(`${normalizeBaseUrl(options.baseUrl ?? NEWS_SERVICE_URL)}/api/v1/news/datasets`);
  } catch {
    throw connectionError();
  }

  if (!response.ok) {
    throw await errorFromResponse(response, "Не удалось загрузить список датасетов");
  }

  return (await response.json()) as DatasetListResponse;
}

export async function activateDataset(datasetId: string, options: ApiOptions = {}): Promise<ActiveDataset> {
  const fetcher = options.fetcher ?? fetch;

  let response: Response;
  try {
    response = await fetcher(
      `${normalizeBaseUrl(options.baseUrl ?? NEWS_SERVICE_URL)}/api/v1/news/datasets/${encodeURIComponent(datasetId)}/activate`,
      { method: "POST" },
    );
  } catch {
    throw connectionError();
  }

  if (!response.ok) {
    throw await errorFromResponse(response, "Не удалось активировать датасет");
  }

  return (await response.json()) as ActiveDataset;
}

export async function getActiveDataset(options: ApiOptions = {}): Promise<ActiveDataset | null> {
  const fetcher = options.fetcher ?? fetch;

  let response: Response;
  try {
    response = await fetcher(`${normalizeBaseUrl(options.baseUrl ?? NEWS_SERVICE_URL)}/api/v1/news/datasets/active`);
  } catch {
    throw connectionError();
  }

  if (!response.ok) {
    throw await errorFromResponse(response, "Не удалось получить активный датасет");
  }

  if (response.status === 204) {
    return null;
  }

  return (await response.json()) as ActiveDataset | null;
}

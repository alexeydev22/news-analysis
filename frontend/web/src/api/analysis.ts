import type { MlReport, MlReportJob, MlReportJobCreated } from "../app/types";
import { ANALYSIS_SERVICE_URL } from "./config";
import { connectionError, errorFromResponse } from "./errors";

type ApiOptions = {
  baseUrl?: string;
  fetcher?: typeof fetch;
};

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/$/, "");
}

export async function startMlReportJob(
  options: ApiOptions = {},
): Promise<MlReportJobCreated> {
  const fetcher = options.fetcher ?? fetch;

  let response: Response;
  try {
    response = await fetcher(`${normalizeBaseUrl(options.baseUrl ?? ANALYSIS_SERVICE_URL)}/api/v1/ml-report/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
  } catch {
    throw connectionError();
  }

  if (!response.ok) {
    throw await errorFromResponse(response, "Не удалось запустить формирование ML-отчета");
  }

  return (await response.json()) as MlReportJobCreated;
}

export async function getMlReportJob(jobId: string, options: ApiOptions = {}): Promise<MlReportJob> {
  const fetcher = options.fetcher ?? fetch;

  let response: Response;
  try {
    response = await fetcher(
      `${normalizeBaseUrl(options.baseUrl ?? ANALYSIS_SERVICE_URL)}/api/v1/ml-report/jobs/${encodeURIComponent(jobId)}`,
    );
  } catch {
    throw connectionError();
  }

  if (!response.ok) {
    throw await errorFromResponse(response, "Не удалось получить статус ML-отчета");
  }

  return (await response.json()) as MlReportJob;
}

export async function getLatestMlReport(options: ApiOptions = {}): Promise<MlReport | null> {
  const fetcher = options.fetcher ?? fetch;

  let response: Response;
  try {
    response = await fetcher(`${normalizeBaseUrl(options.baseUrl ?? ANALYSIS_SERVICE_URL)}/api/v1/ml-report/latest`);
  } catch {
    throw connectionError();
  }

  if (!response.ok) {
    throw await errorFromResponse(response, "Не удалось загрузить ML-отчет");
  }

  if (response.status === 204) {
    return null;
  }

  return (await response.json()) as MlReport | null;
}

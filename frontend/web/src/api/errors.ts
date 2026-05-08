export class ApiError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
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

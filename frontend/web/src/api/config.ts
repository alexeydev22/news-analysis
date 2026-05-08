function trimTrailingSlash(value: string): string {
  return value.replace(/\/$/, "");
}

export const API_GATEWAY_URL = trimTrailingSlash(
  import.meta.env.VITE_API_GATEWAY_URL ?? "http://localhost:8000",
);

export const NEWS_SERVICE_URL = trimTrailingSlash(
  import.meta.env.VITE_NEWS_SERVICE_URL ?? "http://localhost:8004",
);

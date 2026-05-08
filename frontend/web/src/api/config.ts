function trimTrailingSlash(value: string): string {
  return value.replace(/\/$/, "");
}

export const API_GATEWAY_URL = trimTrailingSlash(
  import.meta.env.VITE_API_GATEWAY_URL ?? "/api-gateway",
);

export const NEWS_SERVICE_URL = trimTrailingSlash(
  import.meta.env.VITE_NEWS_SERVICE_URL ?? "/news-service",
);

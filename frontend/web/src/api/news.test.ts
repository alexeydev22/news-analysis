import { describe, expect, it, vi } from "vitest";

import { previewFixture } from "../test/fixtures";
import { indexNewsDataset, previewNews } from "./news";

describe("news api", () => {
  it("loads preview documents", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json(previewFixture));

    const response = await previewNews(
      { limit: 5 },
      { baseUrl: "http://localhost:8004", fetcher: fetchMock },
    );

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8004/api/v1/news/preview?limit=5");
    expect(response).toEqual(previewFixture);
  });

  it("indexes the local dataset", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json({
        loaded_count: 10,
        indexed_count: 10,
        collection_name: "economic_news",
      }),
    );

    const response = await indexNewsDataset(
      { limit: 10 },
      { baseUrl: "http://localhost:8004", fetcher: fetchMock },
    );

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8004/api/v1/news/index", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ limit: 10 }),
    });
    expect(response.indexed_count).toBe(10);
  });
});

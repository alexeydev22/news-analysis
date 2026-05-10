import { describe, expect, it, vi } from "vitest";

import { previewFixture } from "../test/fixtures";
import {
  activateDataset,
  getActiveDataset,
  indexNewsDataset,
  listDatasets,
  previewNews,
  uploadDataset,
} from "./news";

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

  it("uploads a csv dataset as form data", async () => {
    const uploaded = {
      dataset_id: "macro",
      filename: "macro.csv",
      size_bytes: 32,
      uploaded_at: "2026-05-08T10:00:00Z",
    };
    const fetchMock = vi.fn().mockResolvedValue(Response.json(uploaded));
    const file = new File(["id,title\n1,GDP"], "macro.csv", { type: "text/csv" });

    const response = await uploadDataset(file, {
      baseUrl: "http://localhost:8004",
      fetcher: fetchMock,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8004/api/v1/news/datasets/upload",
      expect.objectContaining({ method: "POST", body: expect.any(FormData) }),
    );
    const body = fetchMock.mock.calls[0][1].body as FormData;
    expect(body.get("file")).toBe(file);
    expect(response).toEqual(uploaded);
  });

  it("lists uploaded datasets", async () => {
    const payload = {
      datasets: [
        {
          dataset_id: "macro",
          filename: "macro.csv",
          size_bytes: 32,
          uploaded_at: "2026-05-08T10:00:00Z",
        },
      ],
    };
    const fetchMock = vi.fn().mockResolvedValue(Response.json(payload));

    const response = await listDatasets({
      baseUrl: "http://localhost:8004",
      fetcher: fetchMock,
    });

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8004/api/v1/news/datasets");
    expect(response).toEqual(payload);
  });

  it("activates an uploaded dataset", async () => {
    const active = {
      dataset_id: "macro",
      filename: "macro.csv",
      activated_at: "2026-05-08T10:01:00Z",
    };
    const fetchMock = vi.fn().mockResolvedValue(Response.json(active));

    const response = await activateDataset("macro", {
      baseUrl: "http://localhost:8004",
      fetcher: fetchMock,
    });

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8004/api/v1/news/datasets/macro/activate", {
      method: "POST",
    });
    expect(response).toEqual(active);
  });

  it("loads active dataset", async () => {
    const active = {
      dataset_id: "macro",
      filename: "macro.csv",
      activated_at: "2026-05-08T10:01:00Z",
    };
    const fetchMock = vi.fn().mockResolvedValue(Response.json(active));

    const response = await getActiveDataset({
      baseUrl: "http://localhost:8004",
      fetcher: fetchMock,
    });

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8004/api/v1/news/datasets/active");
    expect(response).toEqual(active);
  });

  it("returns null when no dataset is active", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));

    const response = await getActiveDataset({
      baseUrl: "http://localhost:8004",
      fetcher: fetchMock,
    });

    expect(response).toBeNull();
  });
});

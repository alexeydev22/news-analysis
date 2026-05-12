import { describe, expect, it, vi } from "vitest";

import { mlReportFixture, topicForecastFixture } from "../test/fixtures";
import {
  generateGroqForecast,
  getLatestMlReport,
  getLatestTopicForecast,
  getMlReportJob,
  getTopicForecastJob,
  startMlReportJob,
  startTopicForecastJob,
} from "./analysis";

describe("analysis api", () => {
  it("starts an ml report job", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ job_id: "job-1", status: "queued" }));

    const response = await startMlReportJob({ baseUrl: "http://localhost:8010", fetcher: fetchMock });

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8010/api/v1/ml-report/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(response).toEqual({ job_id: "job-1", status: "queued" });
  });

  it("loads job status and latest report", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        Response.json({
          job_id: "job-1",
          status: "succeeded",
          message: "ready",
          report_path: "reports/ml.json",
        }),
      )
      .mockResolvedValueOnce(Response.json(mlReportFixture));

    const job = await getMlReportJob("job-1", {
      baseUrl: "http://localhost:8010",
      fetcher: fetchMock,
    });
    const report = await getLatestMlReport({
      baseUrl: "http://localhost:8010",
      fetcher: fetchMock,
    });

    expect(fetchMock).toHaveBeenNthCalledWith(1, "http://localhost:8010/api/v1/ml-report/jobs/job-1");
    expect(fetchMock).toHaveBeenNthCalledWith(2, "http://localhost:8010/api/v1/ml-report/latest");
    expect(job.status).toBe("succeeded");
    expect(report).toEqual(mlReportFixture);
  });

  it("returns null when latest report is empty", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));

    const report = await getLatestMlReport({
      baseUrl: "http://localhost:8010",
      fetcher: fetchMock,
    });

    expect(report).toBeNull();
  });

  it("starts a topic forecast job", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ job_id: "topic-job-1", status: "queued" }));

    const response = await startTopicForecastJob({ baseUrl: "http://localhost:8010", fetcher: fetchMock });

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8010/api/v1/topic-forecast/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(response).toEqual({ job_id: "topic-job-1", status: "queued" });
  });

  it("loads topic forecast job status and latest report", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        Response.json({
          job_id: "topic-job-1",
          status: "succeeded",
          message: "ready",
          report_path: "reports/topic-forecast/latest.json",
        }),
      )
      .mockResolvedValueOnce(Response.json(topicForecastFixture));

    const job = await getTopicForecastJob("topic-job-1", {
      baseUrl: "http://localhost:8010",
      fetcher: fetchMock,
    });
    const forecast = await getLatestTopicForecast({
      baseUrl: "http://localhost:8010",
      fetcher: fetchMock,
    });

    expect(fetchMock).toHaveBeenNthCalledWith(1, "http://localhost:8010/api/v1/topic-forecast/jobs/topic-job-1");
    expect(fetchMock).toHaveBeenNthCalledWith(2, "http://localhost:8010/api/v1/topic-forecast/latest");
    expect(job.status).toBe("succeeded");
    expect(forecast).toEqual(topicForecastFixture);
  });

  it("returns null when latest topic forecast is empty", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));

    const forecast = await getLatestTopicForecast({
      baseUrl: "http://localhost:8010",
      fetcher: fetchMock,
    });

    expect(forecast).toBeNull();
  });

  it("generates a Groq forecast for a topic", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json({
        provider: "groq",
        model_name: "qwen/qwen3-32b",
        scope: "topic",
        target_id: "topic-1",
        prediction: "Groq видит умеренно позитивный сценарий.",
        disclaimer: "Это аналитический сценарий, а не финансовая рекомендация.",
        metadata: {},
      }),
    );
    const topic = topicForecastFixture.model_reports![0].topics[0];

    const response = await generateGroqForecast(
      {
        scope: "topic",
        model_name: topicForecastFixture.model_reports![0].model_name,
        topic,
        news_id: null,
      },
      { baseUrl: "http://localhost:8010", fetcher: fetchMock },
    );

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8010/api/v1/topic-forecast/groq-predictions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scope: "topic",
        model_name: topicForecastFixture.model_reports![0].model_name,
        topic,
        news_id: null,
      }),
    });
    expect(response.model_name).toBe("qwen/qwen3-32b");
  });

  it("uses backend detail when Groq forecast generation fails", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json({ detail: "GROQ API key is not configured" }, { status: 503 }),
    );
    const topic = topicForecastFixture.model_reports![0].topics[0];

    await expect(
      generateGroqForecast(
        {
          scope: "topic",
          model_name: topicForecastFixture.model_reports![0].model_name,
          topic,
          news_id: null,
        },
        { baseUrl: "http://localhost:8010", fetcher: fetchMock },
      ),
    ).rejects.toThrow("GROQ API key is not configured");
  });
});

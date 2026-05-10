import { describe, expect, it, vi } from "vitest";

import { mlReportFixture } from "../test/fixtures";
import { getLatestMlReport, getMlReportJob, startMlReportJob } from "./analysis";

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
});

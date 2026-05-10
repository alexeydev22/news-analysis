import { useEffect, useRef, useState } from "react";

import { getLatestMlReport, getMlReportJob, startMlReportJob } from "../api/analysis";
import { streamChat } from "../api/chatStream";
import { ApiError } from "../api/errors";
import {
  activateDataset,
  getActiveDataset,
  indexNewsDataset,
  listDatasets,
  previewNews,
  uploadDataset,
} from "../api/news";
import { ChatPanel } from "../components/ChatPanel";
import { ControlsPanel } from "../components/ControlsPanel";
import { DatasetUpload } from "../components/DatasetUpload";
import { MlReportPanel } from "../components/MlReportPanel";
import { NewsPreview } from "../components/NewsPreview";
import { SourcesPanel } from "../components/SourcesPanel";
import { Timeline } from "../components/Timeline";
import type {
  ActiveDataset,
  AnalysisModelName,
  ChatResponse,
  ChatStreamEvent,
  ImpactSummary,
  IndexNewsDatasetResponse,
  MlReport,
  MlReportJobStatus,
  NewsDocument,
  PreviewNewsResponse,
  UploadedDataset,
} from "./types";
import styles from "./App.module.css";

function messageFromError(error: unknown): string {
  return error instanceof ApiError ? error.message : "Не удалось выполнить действие";
}

function clampLimit(value: number): number {
  if (!Number.isFinite(value)) {
    return 1;
  }
  return Math.min(20, Math.max(1, value));
}

function isChatResponse(data: Record<string, unknown>): data is ChatResponse {
  return typeof data.answer === "string" && Array.isArray(data.sources);
}

function isSourcesFound(data: Record<string, unknown>): data is { sources: NewsDocument[] } {
  return Array.isArray(data.sources);
}

function isAnalysisCompleted(data: Record<string, unknown>): data is { impact_summaries: ImpactSummary[] } {
  return Array.isArray(data.impact_summaries);
}

function streamErrorMessage(): string {
  return "Не удалось завершить потоковый ответ";
}

export function App() {
  const [analysisModel, setAnalysisModel] = useState<AnalysisModelName>("tfidf-logreg");
  const [limit, setLimit] = useState("5");
  const [source, setSource] = useState("");
  const [question, setQuestion] = useState("");
  const [events, setEvents] = useState<ChatStreamEvent[]>([]);
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<NewsDocument[]>([]);
  const [impactSummaries, setImpactSummaries] = useState<ImpactSummary[]>([]);
  const [preview, setPreview] = useState<PreviewNewsResponse | null>(null);
  const [indexResult, setIndexResult] = useState<IndexNewsDatasetResponse | null>(null);
  const [datasets, setDatasets] = useState<UploadedDataset[]>([]);
  const [activeDataset, setActiveDataset] = useState<ActiveDataset | null>(null);
  const [mlReport, setMlReport] = useState<MlReport | null>(null);
  const [mlReportStatus, setMlReportStatus] = useState<MlReportJobStatus | null>(null);
  const [mlReportError, setMlReportError] = useState<string | null>(null);
  const [isStreaming, setStreaming] = useState(false);
  const [isPreviewLoading, setPreviewLoading] = useState(false);
  const [isIndexLoading, setIndexLoading] = useState(false);
  const [isUploading, setUploading] = useState(false);
  const [isMlReportLoading, setMlReportLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const datasetRequestIdRef = useRef(0);
  const mlReportPollRef = useRef<number | null>(null);

  function nextDatasetRequestId(): number {
    datasetRequestIdRef.current += 1;
    return datasetRequestIdRef.current;
  }

  function isLatestDatasetRequest(requestId: number): boolean {
    return datasetRequestIdRef.current === requestId;
  }

  useEffect(() => {
    let isMounted = true;

    async function loadDatasets() {
      const requestId = nextDatasetRequestId();
      try {
        const [datasetList, active] = await Promise.all([listDatasets(), getActiveDataset()]);
        if (isMounted && isLatestDatasetRequest(requestId)) {
          setDatasets(datasetList.datasets);
          setActiveDataset(active);
        }
      } catch {
        if (isMounted && isLatestDatasetRequest(requestId)) {
          setDatasets([]);
          setActiveDataset(null);
        }
      }
    }

    void loadDatasets();

    return () => {
      isMounted = false;
      nextDatasetRequestId();
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadLatestReport() {
      try {
        const report = await getLatestMlReport();
        if (isMounted) {
          setMlReport(report);
        }
      } catch {
        if (isMounted) {
          setMlReport(null);
        }
      }
    }

    void loadLatestReport();

    return () => {
      isMounted = false;
      if (mlReportPollRef.current !== null) {
        window.clearTimeout(mlReportPollRef.current);
      }
    };
  }, []);

  function applyStreamEvent(event: ChatStreamEvent) {
    if (event.event === "sources_found" && isSourcesFound(event.data)) {
      setSources(event.data.sources);
    }
    if (event.event === "analysis_completed" && isAnalysisCompleted(event.data)) {
      setImpactSummaries(event.data.impact_summaries);
    }
    if (event.event === "answer_completed" && isChatResponse(event.data)) {
      setAnswer(event.data.answer);
      setSources(event.data.sources);
      setImpactSummaries(event.data.impact_summaries);
    }
    if (event.event === "error") {
      setError(streamErrorMessage());
    }
  }

  async function handleSubmit() {
    setStreaming(true);
    setError(null);
    setEvents([]);
    setAnswer("");
    setSources([]);
    setImpactSummaries([]);

    try {
      await streamChat(
        {
          question,
          analysis_model: analysisModel,
          limit: clampLimit(Number(limit)),
          source: source.trim() || null,
        },
        {
          onEvent: (event) => {
            setEvents((currentEvents) => [...currentEvents, event]);
            applyStreamEvent(event);
          },
        },
      );
    } catch (streamError) {
      setError(messageFromError(streamError));
    } finally {
      setStreaming(false);
    }
  }

  async function handlePreview() {
    setPreviewLoading(true);
    setError(null);
    try {
      setPreview(await previewNews({ limit: 5 }));
    } catch (previewError) {
      setError(messageFromError(previewError));
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleIndex() {
    setIndexLoading(true);
    setError(null);
    try {
      setIndexResult(await indexNewsDataset({ limit: 100 }));
    } catch (indexError) {
      setError(messageFromError(indexError));
    } finally {
      setIndexLoading(false);
    }
  }

  async function handleUploadDataset(file: File) {
    const requestId = nextDatasetRequestId();
    setUploading(true);
    setError(null);
    try {
      const uploaded = await uploadDataset(file);
      const active = await activateDataset(uploaded.dataset_id);
      if (isLatestDatasetRequest(requestId)) {
        setActiveDataset(active);
      }
      const datasetList = await listDatasets();
      if (isLatestDatasetRequest(requestId)) {
        setDatasets(datasetList.datasets);
      }
    } catch (uploadError) {
      if (isLatestDatasetRequest(requestId)) {
        setError(messageFromError(uploadError));
      }
    } finally {
      setUploading(false);
    }
  }

  async function handleActivateDataset(datasetId: string) {
    const requestId = nextDatasetRequestId();
    setError(null);
    try {
      const active = await activateDataset(datasetId);
      if (isLatestDatasetRequest(requestId)) {
        setActiveDataset(active);
      }
    } catch (activateError) {
      if (isLatestDatasetRequest(requestId)) {
        setError(messageFromError(activateError));
      }
    }
  }

  async function loadLatestMlReport() {
    setMlReport(await getLatestMlReport());
  }

  function scheduleMlReportPoll(jobId: string) {
    if (mlReportPollRef.current !== null) {
      window.clearTimeout(mlReportPollRef.current);
    }

    mlReportPollRef.current = window.setTimeout(() => {
      void pollMlReportJob(jobId);
    }, 1500);
  }

  async function pollMlReportJob(jobId: string) {
    try {
      const job = await getMlReportJob(jobId);
      setMlReportStatus(job.status);

      if (job.status === "succeeded") {
        await loadLatestMlReport();
        setMlReportLoading(false);
        return;
      }

      if (job.status === "failed") {
        setMlReportError(job.message || "Не удалось сформировать ML-отчет");
        setMlReportLoading(false);
        return;
      }

      scheduleMlReportPoll(job.job_id);
    } catch (jobError) {
      setMlReportError(messageFromError(jobError));
      setMlReportLoading(false);
    }
  }

  async function handleGenerateMlReport() {
    setMlReportLoading(true);
    setMlReportError(null);
    try {
      const job = await startMlReportJob();
      setMlReportStatus(job.status);
      if (job.status === "succeeded") {
        await loadLatestMlReport();
        setMlReportLoading(false);
        return;
      }
      if (job.status === "failed") {
        setMlReportError("Не удалось сформировать ML-отчет");
        setMlReportLoading(false);
        return;
      }
      scheduleMlReportPoll(job.job_id);
    } catch (reportError) {
      setMlReportError(messageFromError(reportError));
      setMlReportLoading(false);
    }
  }

  return (
    <main className={styles.shell}>
      <div className={styles.controls}>
        <ControlsPanel
          analysisModel={analysisModel}
          limit={limit}
          source={source}
          isPreviewLoading={isPreviewLoading}
          isIndexLoading={isIndexLoading}
          datasetUploadSlot={
            <DatasetUpload
              datasets={datasets}
              activeDataset={activeDataset}
              isUploading={isUploading}
              onUpload={(file) => {
                void handleUploadDataset(file);
              }}
              onActivate={(datasetId) => {
                void handleActivateDataset(datasetId);
              }}
            />
          }
          onAnalysisModelChange={setAnalysisModel}
          onLimitChange={setLimit}
          onSourceChange={setSource}
          onPreview={handlePreview}
          onIndex={handleIndex}
        />
        <NewsPreview preview={preview} indexResult={indexResult} />
        <MlReportPanel
          report={mlReport}
          status={mlReportStatus}
          error={mlReportError}
          isLoading={isMlReportLoading}
          onGenerate={() => {
            void handleGenerateMlReport();
          }}
        />
      </div>
      <div className={styles.chat}>
        <ChatPanel
          question={question}
          answer={answer}
          isStreaming={isStreaming}
          error={error}
          onQuestionChange={setQuestion}
          onSubmit={handleSubmit}
        />
        <Timeline events={events} />
      </div>
      <div className={styles.sources}>
        <SourcesPanel sources={sources} impactSummaries={impactSummaries} />
      </div>
    </main>
  );
}

import { useState } from "react";

import { streamChat } from "../api/chatStream";
import { ApiError } from "../api/errors";
import { indexNewsDataset, previewNews } from "../api/news";
import { ChatPanel } from "../components/ChatPanel";
import { ControlsPanel } from "../components/ControlsPanel";
import { NewsPreview } from "../components/NewsPreview";
import { SourcesPanel } from "../components/SourcesPanel";
import { Timeline } from "../components/Timeline";
import type {
  AnalysisModelName,
  ChatResponse,
  ChatStreamEvent,
  ImpactSummary,
  IndexNewsDatasetResponse,
  NewsDocument,
  PreviewNewsResponse,
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
  const [isStreaming, setStreaming] = useState(false);
  const [isPreviewLoading, setPreviewLoading] = useState(false);
  const [isIndexLoading, setIndexLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <main className={styles.shell}>
      <div className={styles.controls}>
        <ControlsPanel
          analysisModel={analysisModel}
          limit={limit}
          source={source}
          isPreviewLoading={isPreviewLoading}
          isIndexLoading={isIndexLoading}
          onAnalysisModelChange={setAnalysisModel}
          onLimitChange={setLimit}
          onSourceChange={setSource}
          onPreview={handlePreview}
          onIndex={handleIndex}
        />
        <NewsPreview preview={preview} indexResult={indexResult} />
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

import type { AnalysisModelName } from "../app/types";

type ControlsPanelProps = {
  analysisModel: AnalysisModelName;
  limit: string;
  source: string;
  isPreviewLoading: boolean;
  isIndexLoading: boolean;
  onAnalysisModelChange: (value: AnalysisModelName) => void;
  onLimitChange: (value: string) => void;
  onSourceChange: (value: string) => void;
  onPreview: () => void;
  onIndex: () => void;
};

const ANALYSIS_MODELS: AnalysisModelName[] = [
  "tfidf-logreg",
  "embedding-logreg",
  "tiny-transformer-classifier",
];

export function ControlsPanel({
  analysisModel,
  limit,
  source,
  isPreviewLoading,
  isIndexLoading,
  onAnalysisModelChange,
  onLimitChange,
  onSourceChange,
  onPreview,
  onIndex,
}: ControlsPanelProps) {
  return (
    <aside aria-label="Настройки анализа">
      <p>Локальный RAG-конвейер</p>
      <h1>Диалоговая система анализа экономических новостей</h1>

      <label>
        <span>Модель анализа</span>
        <select
          aria-label="Модель анализа"
          value={analysisModel}
          onChange={(event) => onAnalysisModelChange(event.target.value as AnalysisModelName)}
        >
          {ANALYSIS_MODELS.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
      </label>

      <label>
        <span>Лимит источников</span>
        <input
          aria-label="Лимит источников"
          type="number"
          min={1}
          max={20}
          value={limit}
          onChange={(event) => onLimitChange(event.target.value)}
        />
      </label>

      <label>
        <span>Источник</span>
        <input
          aria-label="Источник"
          value={source}
          placeholder="все источники"
          onChange={(event) => onSourceChange(event.target.value)}
        />
      </label>

      <div className="controlActions">
        <button type="button" onClick={onPreview} disabled={isPreviewLoading}>
          {isPreviewLoading ? "Загрузка предпросмотра" : "Предпросмотр CSV"}
        </button>
        <button type="button" onClick={onIndex} disabled={isIndexLoading}>
          {isIndexLoading ? "Индексация" : "Индексировать CSV"}
        </button>
      </div>
    </aside>
  );
}

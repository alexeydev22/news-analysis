import type { AnalysisModelName } from "../app/types";

type AnalysisSettingsProps = {
  analysisModel: AnalysisModelName;
  limit: string;
  source: string;
  onAnalysisModelChange: (value: AnalysisModelName) => void;
  onLimitChange: (value: string) => void;
  onSourceChange: (value: string) => void;
};

const ANALYSIS_MODELS: AnalysisModelName[] = [
  "tfidf-logreg",
  "embedding-logreg",
  "tiny-transformer-classifier",
];

export function AnalysisSettings({
  analysisModel,
  limit,
  source,
  onAnalysisModelChange,
  onLimitChange,
  onSourceChange,
}: AnalysisSettingsProps) {
  return (
    <div>
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
    </div>
  );
}

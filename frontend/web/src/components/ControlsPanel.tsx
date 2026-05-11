import type { ReactNode } from "react";

import type { AnalysisModelName } from "../app/types";
import { AnalysisSettings } from "./AnalysisSettings";

type ControlsPanelProps = {
  analysisModel: AnalysisModelName;
  limit: string;
  source: string;
  isPreviewLoading: boolean;
  isIndexLoading: boolean;
  datasetUploadSlot: ReactNode;
  onAnalysisModelChange: (value: AnalysisModelName) => void;
  onLimitChange: (value: string) => void;
  onSourceChange: (value: string) => void;
  onPreview: () => void;
  onIndex: () => void;
};

export function ControlsPanel({
  analysisModel,
  limit,
  source,
  isPreviewLoading,
  isIndexLoading,
  datasetUploadSlot,
  onAnalysisModelChange,
  onLimitChange,
  onSourceChange,
  onPreview,
  onIndex,
}: ControlsPanelProps) {
  return (
    <aside aria-label="Настройки данных">
      <h2>Параметры индексации</h2>
      <AnalysisSettings
        analysisModel={analysisModel}
        limit={limit}
        source={source}
        onAnalysisModelChange={onAnalysisModelChange}
        onLimitChange={onLimitChange}
        onSourceChange={onSourceChange}
      />

      {datasetUploadSlot}

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

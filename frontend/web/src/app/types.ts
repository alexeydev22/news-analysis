export type AnalysisModelName = "tfidf-logreg" | "embedding-logreg" | "tiny-transformer-classifier";

export type ImpactLabel = "positive" | "neutral" | "negative";

export type NewsDocument = {
  id: string;
  title: string;
  text: string;
  source: string;
  score?: number;
  published_at: string | null;
  metadata: Record<string, unknown>;
};

export type ImpactSummary = {
  news_id: string;
  model_name: AnalysisModelName;
  impact: ImpactLabel;
  confidence: number | null;
  explanation: string;
};

export type ChatRequest = {
  question: string;
  analysis_model: AnalysisModelName;
  limit: number;
  source: string | null;
};

export type ChatResponse = {
  answer: string;
  sources: NewsDocument[];
  impact_summaries: ImpactSummary[];
  analysis_model: AnalysisModelName;
  metadata: Record<string, unknown>;
};

export type ChatStreamEvent = {
  event: string;
  data: Record<string, unknown>;
};

export type PreviewNewsResponse = {
  documents: NewsDocument[];
  total_count: number;
};

export type IndexNewsDatasetResponse = {
  loaded_count: number;
  indexed_count: number;
  collection_name: string;
};

export type UploadedDataset = {
  dataset_id: string;
  filename: string;
  size_bytes: number;
  uploaded_at: string;
};

export type DatasetListResponse = {
  datasets: UploadedDataset[];
};

export type ActiveDataset = {
  dataset_id: string;
  filename: string;
  activated_at: string;
};

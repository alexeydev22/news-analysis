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

export type MlReportJobStatus = "queued" | "started" | "succeeded" | "failed";

export type TopicForecastJobStatus = "queued" | "started" | "succeeded" | "failed";

export type MlReportJobCreated = {
  job_id: string;
  status: MlReportJobStatus;
};

export type MlReportJob = {
  job_id: string;
  status: MlReportJobStatus;
  message: string | null;
  report_path: string | null;
};

export type TopicForecastJobCreated = {
  job_id: string;
  status: TopicForecastJobStatus;
};

export type TopicForecastJob = {
  job_id: string;
  status: TopicForecastJobStatus;
  message: string | null;
  report_path: string | null;
};

export type MlReportModel = {
  model_name: string;
  validation_accuracy: number | null;
  validation_macro_f1: number | null;
  test_accuracy: number | null;
  test_macro_f1: number | null;
  inference_seconds_per_sample: number | null;
  confusion_matrix: {
    labels: string[];
    matrix: number[][];
  } | null;
};

export type MlReport = {
  generated_at: string;
  dataset: {
    path: string;
    row_count: number;
    class_distribution: Record<string, number>;
  };
  models: MlReportModel[];
  best_model: MlReportModel | null;
  top_features: Record<string, Record<string, string[]>>;
};

export type TopicForecastNewsItem = {
  id: string;
  title: string;
  text: string;
  source: string;
  impact: ImpactLabel;
  score: number | null;
};

export type TopicForecastTopic = {
  topic_id: string;
  title: string;
  summary: string;
  overall_impact: ImpactLabel;
  confidence: number | null;
  positive_count: number;
  neutral_count: number;
  negative_count: number;
  forecast: string;
  arguments: string[];
  risks: string[];
  news: TopicForecastNewsItem[];
};

export type TopicForecastModelReport = {
  model_name: string;
  topics: TopicForecastTopic[];
  error: string | null;
};

export type TopicForecast = {
  generated_at: string;
  topics: TopicForecastTopic[];
  model_reports?: TopicForecastModelReport[];
  metadata: Record<string, unknown>;
};

export type GroqForecastScope = "topic" | "news";

export type GroqForecastRequest = {
  scope: GroqForecastScope;
  model_name: string;
  topic: TopicForecastTopic;
  news_id: string | null;
};

export type GroqForecastResponse = {
  provider: string;
  model_name: string;
  scope: GroqForecastScope;
  target_id: string;
  prediction: string;
  disclaimer: string;
  metadata: Record<string, unknown>;
};

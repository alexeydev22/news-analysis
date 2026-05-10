import type { ChatResponse, MlReport, NewsDocument, PreviewNewsResponse } from "../app/types";

export const sourceFixture: NewsDocument = {
  id: "news-1",
  title: "ВВП вырос",
  text: "ВВП вырос на 2 процента.",
  source: "Демо",
  score: 0.75,
  published_at: null,
  metadata: { sector: "macro" },
};

export const chatResponseFixture: ChatResponse = {
  answer: "Рост ВВП обычно поддерживает рынок.",
  sources: [sourceFixture],
  impact_summaries: [
    {
      news_id: "news-1",
      model_name: "tfidf-logreg",
      impact: "positive",
      confidence: 0.82,
      explanation: "Рост ВВП обычно поддерживает рынок.",
    },
  ],
  analysis_model: "tfidf-logreg",
  metadata: {
    dialog_model_name: "Qwen3-0.6B-Instruct-GGUF",
    used_context_ids: ["news-1"],
  },
};

export const previewFixture: PreviewNewsResponse = {
  total_count: 1,
  documents: [
    {
      id: "news-1",
      title: "ВВП вырос",
      text: "ВВП вырос на 2 процента.",
      source: "Демо",
      published_at: null,
      metadata: { row_number: 2 },
    },
  ],
};

export const mlReportFixture: MlReport = {
  generated_at: "2026-05-09T12:00:00Z",
  dataset: {
    path: "data/news.csv",
    row_count: 120,
    class_distribution: {
      positive: 50,
      neutral: 45,
      negative: 25,
    },
  },
  models: [
    {
      model_name: "tfidf-logreg",
      validation_accuracy: 0.91,
      validation_macro_f1: 0.89,
      test_accuracy: 0.9,
      test_macro_f1: 0.88,
      inference_seconds_per_sample: 0.004,
      confusion_matrix: {
        labels: ["positive", "neutral", "negative"],
        matrix: [
          [42, 5, 3],
          [4, 38, 3],
          [2, 3, 20],
        ],
      },
    },
    {
      model_name: "embedding-logreg",
      validation_accuracy: 0.87,
      validation_macro_f1: 0.85,
      test_accuracy: 0.86,
      test_macro_f1: 0.84,
      inference_seconds_per_sample: 0.012,
      confusion_matrix: null,
    },
  ],
  best_model: {
    model_name: "tfidf-logreg",
    validation_accuracy: 0.91,
    validation_macro_f1: 0.89,
    test_accuracy: 0.9,
    test_macro_f1: 0.88,
    inference_seconds_per_sample: 0.004,
    confusion_matrix: null,
  },
  top_features: {
    "tfidf-logreg": {
      positive: ["ввп", "инфляция", "ставка"],
    },
  },
};

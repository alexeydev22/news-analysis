import type { ChatResponse, NewsDocument, PreviewNewsResponse } from "../app/types";

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

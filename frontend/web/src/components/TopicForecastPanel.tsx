import type {
  GroqForecastRequest,
  GroqForecastResponse,
  ImpactLabel,
  TopicForecast,
  TopicForecastJobStatus,
  TopicForecastNewsItem,
} from "../app/types";
import styles from "../app/App.module.css";

type TopicForecastPanelProps = {
  forecast: TopicForecast | null;
  status: TopicForecastJobStatus | null;
  error: string | null;
  isLoading: boolean;
  groqForecasts: Record<string, GroqForecastResponse>;
  groqForecastLoadingKeys: Record<string, boolean>;
  groqForecastError: string | null;
  onGenerate: () => void;
  onGenerateGroqForecast: (request: GroqForecastRequest, forecastGeneratedAt: string) => void;
};

const STATUS_LABELS: Record<TopicForecastJobStatus, string> = {
  queued: "в очереди",
  started: "выполняется",
  succeeded: "готов",
  failed: "ошибка",
};

const IMPACT_LABELS: Record<ImpactLabel, string> = {
  positive: "позитивное",
  neutral: "нейтральное",
  negative: "негативное",
};

function formatMetric(value: number | null): string {
  return value !== null && Number.isFinite(value) ? value.toFixed(3) : "n/a";
}

function metadataValue(forecast: TopicForecast, key: string): string | null {
  const value = forecast.metadata[key];
  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }
  return null;
}

function renderNewsMeta(news: TopicForecastNewsItem): string {
  const parts = [news.source, IMPACT_LABELS[news.impact]];
  if (typeof news.score === "number") {
    parts.push(news.score.toFixed(2));
  }
  return parts.join(" · ");
}

export function groqForecastKey(request: {
  forecastGeneratedAt: string;
  modelName: string;
  scope: "topic" | "news";
  topicId: string;
  newsId?: string | null;
}): string {
  return [
    request.forecastGeneratedAt,
    request.modelName,
    request.scope,
    request.topicId,
    request.newsId ?? "",
  ].join(":");
}

function renderGroqForecastResult(result: GroqForecastResponse | undefined) {
  if (!result) {
    return null;
  }

  return (
    <div className={styles.groqForecastResult}>
      <strong>{`${result.model_name} · ${result.scope}`}</strong>
      <p>{result.prediction}</p>
      <small>{result.disclaimer}</small>
    </div>
  );
}

export function TopicForecastPanel({
  forecast,
  status,
  error,
  isLoading,
  groqForecasts,
  groqForecastLoadingKeys,
  groqForecastError,
  onGenerate,
  onGenerateGroqForecast,
}: TopicForecastPanelProps) {
  const documentCount = forecast ? metadataValue(forecast, "document_count") : null;
  const fallbackModel = forecast ? (metadataValue(forecast, "model") ?? metadataValue(forecast, "analysis_model")) : null;
  const modelReports =
    forecast && forecast.model_reports && forecast.model_reports.length > 0
      ? forecast.model_reports
      : forecast
        ? [{ model_name: fallbackModel ?? "tfidf-logreg", topics: forecast.topics, error: null }]
        : [];

  return (
    <section className={styles.topicForecast} aria-label="Прогноз по темам">
      <h2>Прогноз по темам</h2>
      <button type="button" onClick={onGenerate} disabled={isLoading}>
        {isLoading ? "Формирование прогноза по темам" : "Сформировать прогноз по темам"}
      </button>
      {status ? <p>Статус: {STATUS_LABELS[status]}</p> : null}
      {error ? (
        <p className={styles.errorText} role="alert">
          {error}
        </p>
      ) : null}
      {groqForecastError ? (
        <p className={styles.errorText} role="alert">
          {groqForecastError}
        </p>
      ) : null}

      {forecast ? (
        <div className={styles.reportContent}>
          <p>Сформировано: {forecast.generated_at}</p>
          {documentCount ? <p>Документов: {documentCount}</p> : null}

          {modelReports.map((modelReport) => (
            <section key={modelReport.model_name}>
              <h3>{`Модель: ${modelReport.model_name}`}</h3>
              {modelReport.error ? <p className={styles.errorText}>{modelReport.error}</p> : null}

              <div className={styles.topicCards}>
                {modelReport.topics.map((topic) => {
                  const topicGroqKey = groqForecastKey({
                    forecastGeneratedAt: forecast.generated_at,
                    modelName: modelReport.model_name,
                    scope: "topic",
                    topicId: topic.topic_id,
                  });
                  return (
                    <article className={styles.topicCard} key={`${modelReport.model_name}-${topic.topic_id}`}>
                      <h4>{topic.title}</h4>
                      <p>{topic.summary}</p>
                      <div className={styles.forecastActions}>
                        <button
                          type="button"
                          disabled={Boolean(groqForecastLoadingKeys[topicGroqKey])}
                          onClick={() =>
                            onGenerateGroqForecast(
                              {
                                scope: "topic",
                                model_name: modelReport.model_name,
                                topic,
                                news_id: null,
                              },
                              forecast.generated_at,
                            )
                          }
                        >
                          {groqForecastLoadingKeys[topicGroqKey] ? "Формирование Groq-прогноза" : "Groq-прогноз темы"}
                        </button>
                      </div>
                      {renderGroqForecastResult(groqForecasts[topicGroqKey])}
                      <ul className={styles.inlineList}>
                        <li>Общее влияние: {IMPACT_LABELS[topic.overall_impact]}</li>
                        <li>Уверенность: {formatMetric(topic.confidence)}</li>
                        <li>Позитивных: {topic.positive_count}</li>
                        <li>Нейтральных: {topic.neutral_count}</li>
                        <li>Негативных: {topic.negative_count}</li>
                      </ul>

                      <section>
                        <h5>Прогноз</h5>
                        <p>{topic.forecast}</p>
                      </section>

                      <section>
                        <h5>Аргументы</h5>
                        {topic.arguments.length > 0 ? (
                          <ul className={styles.sectionList}>
                            {topic.arguments.map((argument) => (
                              <li key={argument}>{argument}</li>
                            ))}
                          </ul>
                        ) : (
                          <p>Аргументы не указаны.</p>
                        )}
                      </section>

                      <section>
                        <h5>Риски</h5>
                        {topic.risks.length > 0 ? (
                          <ul className={styles.sectionList}>
                            {topic.risks.map((risk) => (
                              <li key={risk}>{risk}</li>
                            ))}
                          </ul>
                        ) : (
                          <p>Риски не указаны.</p>
                        )}
                      </section>

                      <section>
                        <h5>Новости</h5>
                        {topic.news.length > 0 ? (
                          <ul className={styles.newsList}>
                            {topic.news.map((news) => {
                              const newsGroqKey = groqForecastKey({
                                forecastGeneratedAt: forecast.generated_at,
                                modelName: modelReport.model_name,
                                scope: "news",
                                topicId: topic.topic_id,
                                newsId: news.id,
                              });
                              return (
                                <li key={news.id}>
                                  <strong>{news.title}</strong>
                                  <span>{renderNewsMeta(news)}</span>
                                  <button
                                    type="button"
                                    disabled={Boolean(groqForecastLoadingKeys[newsGroqKey])}
                                    onClick={() =>
                                      onGenerateGroqForecast(
                                        {
                                          scope: "news",
                                          model_name: modelReport.model_name,
                                          topic,
                                          news_id: news.id,
                                        },
                                        forecast.generated_at,
                                      )
                                    }
                                  >
                                    {groqForecastLoadingKeys[newsGroqKey]
                                      ? "Формирование Groq-прогноза"
                                      : "Groq-прогноз новости"}
                                  </button>
                                  {renderGroqForecastResult(groqForecasts[newsGroqKey])}
                                </li>
                              );
                            })}
                          </ul>
                        ) : (
                          <p>Новости не указаны.</p>
                        )}
                      </section>
                    </article>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <p>Прогноз еще не сформирован</p>
      )}
    </section>
  );
}

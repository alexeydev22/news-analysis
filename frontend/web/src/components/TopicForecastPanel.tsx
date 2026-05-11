import type { ImpactLabel, TopicForecast, TopicForecastJobStatus, TopicForecastNewsItem } from "../app/types";
import styles from "../app/App.module.css";

type TopicForecastPanelProps = {
  forecast: TopicForecast | null;
  status: TopicForecastJobStatus | null;
  error: string | null;
  isLoading: boolean;
  onGenerate: () => void;
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

export function TopicForecastPanel({ forecast, status, error, isLoading, onGenerate }: TopicForecastPanelProps) {
  const documentCount = forecast ? metadataValue(forecast, "document_count") : null;
  const model = forecast ? (metadataValue(forecast, "model") ?? metadataValue(forecast, "analysis_model")) : null;

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

      {forecast ? (
        <div className={styles.reportContent}>
          <p>Сформировано: {forecast.generated_at}</p>
          {documentCount ? <p>Документов: {documentCount}</p> : null}
          {model ? <p>Модель: {model}</p> : null}

          <div className={styles.topicCards}>
            {forecast.topics.map((topic) => (
              <article className={styles.topicCard} key={topic.topic_id}>
                <h3>{topic.title}</h3>
                <p>{topic.summary}</p>
                <ul className={styles.inlineList}>
                  <li>Общее влияние: {IMPACT_LABELS[topic.overall_impact]}</li>
                  <li>Уверенность: {formatMetric(topic.confidence)}</li>
                  <li>Позитивных: {topic.positive_count}</li>
                  <li>Нейтральных: {topic.neutral_count}</li>
                  <li>Негативных: {topic.negative_count}</li>
                </ul>

                <section>
                  <h4>Прогноз</h4>
                  <p>{topic.forecast}</p>
                </section>

                <section>
                  <h4>Аргументы</h4>
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
                  <h4>Риски</h4>
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
                  <h4>Новости</h4>
                  {topic.news.length > 0 ? (
                    <ul className={styles.newsList}>
                      {topic.news.map((news) => (
                        <li key={news.id}>
                          <strong>{news.title}</strong>
                          <span>{renderNewsMeta(news)}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>Новости не указаны.</p>
                  )}
                </section>
              </article>
            ))}
          </div>
        </div>
      ) : (
        <p>Прогноз еще не сформирован</p>
      )}
    </section>
  );
}

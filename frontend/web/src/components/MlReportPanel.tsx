import type { MlReport, MlReportJobStatus, MlReportModel } from "../app/types";
import styles from "../app/App.module.css";

type MlReportPanelProps = {
  report: MlReport | null;
  status: MlReportJobStatus | null;
  error: string | null;
  isLoading: boolean;
  onGenerate: () => void;
};

const STATUS_LABELS: Record<MlReportJobStatus, string> = {
  queued: "в очереди",
  started: "выполняется",
  succeeded: "готов",
  failed: "ошибка",
};

function formatMetric(value: number | null): string {
  return value !== null && Number.isFinite(value) ? value.toFixed(3) : "n/a";
}

function getDisplayModel(report: MlReport): MlReportModel | null {
  return (
    report.models.find((model) => model.model_name === report.best_model?.model_name) ??
    report.models[0] ??
    null
  );
}

function renderClassDistribution(distribution: Record<string, number>) {
  const entries = Object.entries(distribution);

  if (entries.length === 0) {
    return <p>Распределение классов пустое.</p>;
  }

  return (
    <ul className={styles.inlineList}>
      {entries.map(([label, count]) => (
        <li key={label}>
          {label}: {count}
        </li>
      ))}
    </ul>
  );
}

function renderTopFeatures(report: MlReport) {
  const featuresByClass = report.top_features["tfidf-logreg"] ?? {};
  const entries = Object.entries(featuresByClass);

  if (entries.length === 0) {
    return <p>Топ-признаки tfidf-logreg пока пусты.</p>;
  }

  return (
    <div className={styles.featureGroups}>
      {entries.map(([className, features]) => (
        <div key={className}>
          <h4>{className}</h4>
          <ul className={styles.inlineList}>
            {features.map((feature) => (
              <li key={`${className}-${feature}`}>{feature}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function renderConfusionMatrix(model: MlReportModel | null) {
  if (!model?.confusion_matrix) {
    return <p>Матрица ошибок недоступна.</p>;
  }

  const { labels, matrix } = model.confusion_matrix;

  return (
    <div className={styles.tableScroller}>
      <table className={styles.compactTable} aria-label={`Матрица ошибок ${model.model_name}`}>
        <thead>
          <tr>
            <th>Факт \ прогноз</th>
            {labels.map((label) => (
              <th key={label}>{label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {labels.map((label, rowIndex) => (
            <tr key={label}>
              <th>{label}</th>
              {labels.map((columnLabel, columnIndex) => (
                <td key={columnLabel}>{matrix[rowIndex]?.[columnIndex] ?? 0}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function MlReportPanel({ report, status, error, isLoading, onGenerate }: MlReportPanelProps) {
  const displayModel = report ? getDisplayModel(report) : null;

  return (
    <section className={styles.mlReport} aria-label="ML-отчет">
      <h2>ML-отчет</h2>
      <button type="button" onClick={onGenerate} disabled={isLoading}>
        {isLoading ? "Формирование ML-отчета" : "Сформировать ML-отчет"}
      </button>
      {status ? <p>Статус: {STATUS_LABELS[status]}</p> : null}
      {error ? (
        <p className={styles.errorText} role="alert">
          {error}
        </p>
      ) : null}

      {report ? (
        <div className={styles.reportContent}>
          <p>Лучшая модель: {report.best_model?.model_name ?? "не определена"}</p>
          <p>Строк в датасете: {report.dataset.row_count}</p>
          {renderClassDistribution(report.dataset.class_distribution)}

          <div className={styles.tableScroller}>
            <table className={styles.compactTable}>
              <thead>
                <tr>
                  <th>Модель</th>
                  <th>Val accuracy</th>
                  <th>Val macro F1</th>
                  <th>Test accuracy</th>
                  <th>Test macro F1</th>
                  <th>Inference, сек</th>
                </tr>
              </thead>
              <tbody>
                {report.models.map((model) => (
                  <tr key={model.model_name}>
                    <td>{model.model_name}</td>
                    <td>{formatMetric(model.validation_accuracy)}</td>
                    <td>{formatMetric(model.validation_macro_f1)}</td>
                    <td>{formatMetric(model.test_accuracy)}</td>
                    <td>{formatMetric(model.test_macro_f1)}</td>
                    <td>{formatMetric(model.inference_seconds_per_sample)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3>Матрица ошибок</h3>
          {renderConfusionMatrix(displayModel)}

          <h3>Топ-признаки tfidf-logreg</h3>
          {renderTopFeatures(report)}
        </div>
      ) : (
        <p>Отчет еще не сформирован</p>
      )}
    </section>
  );
}

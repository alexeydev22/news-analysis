import styles from "./App.module.css";

const MODEL_OPTIONS = [
  { label: "Qwen3 0.6B", value: "qwen3-0.6b" },
  { label: "Llama 3.2 1B", value: "llama-3.2-1b" },
];

export function App() {
  return (
    <main className={styles.shell}>
      <section className={styles.workspace} aria-labelledby="app-title">
        <header className={styles.header}>
          <div>
            <p className={styles.eyebrow}>Анализ экономических новостей</p>
            <h1 id="app-title">Economic News Dialog</h1>
          </div>
          <div className={styles.status}>API offline</div>
        </header>

        <div className={styles.layout}>
          <aside className={styles.sidebar} aria-label="Настройки анализа">
            <label className={styles.field}>
              <span>Модель анализа</span>
              <select defaultValue={MODEL_OPTIONS[0].value}>
                {MODEL_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className={styles.field}>
              <span>Лимит источников</span>
              <input min="1" max="10" type="number" defaultValue="5" />
            </label>

            <label className={styles.field}>
              <span>Источник</span>
              <input type="text" defaultValue="data/news.csv" />
            </label>

            <div className={styles.actions}>
              <button type="button">Preview CSV</button>
              <button type="button">Index CSV</button>
            </div>
          </aside>

          <section className={styles.chat} aria-label="Диалоговая система">
            <div className={styles.messages}>
              <p>Ответ появится после отправки вопроса.</p>
            </div>

            <form
              aria-label="Форма вопроса"
              className={styles.composer}
              onSubmit={(event) => {
                event.preventDefault();
              }}
            >
              <label className={styles.question}>
                <span>Вопрос</span>
                <textarea rows={3} placeholder="Как новость повлияет на рынок?" />
              </label>
              <button type="submit">Отправить</button>
            </form>
          </section>

          <aside className={styles.sources} aria-label="Источники анализа">
            <h2>Sources</h2>
            <p>Источники появятся после ответа.</p>
          </aside>
        </div>
      </section>
    </main>
  );
}

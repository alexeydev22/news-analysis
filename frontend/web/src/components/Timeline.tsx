import type { ChatStreamEvent } from "../app/types";

type TimelineProps = {
  events: ChatStreamEvent[];
};

const EVENT_LABELS: Record<string, string> = {
  chat_started: "чат запущен",
  search_started: "поиск запущен",
  sources_found: "источники найдены",
  analysis_started: "анализ запущен",
  analysis_completed: "анализ завершен",
  answer_started: "формирование ответа",
  answer_completed: "ответ сформирован",
  done: "готово",
  error: "ошибка",
};

export function Timeline({ events }: TimelineProps) {
  return (
    <section aria-label="Ход обработки">
      <h2>Ход обработки</h2>
      {events.length === 0 ? (
        <p>События обработки появятся во время ответа.</p>
      ) : (
        <ol>
          {events.map((event, index) => (
            <li key={`${event.event}-${index}`}>{EVENT_LABELS[event.event] ?? event.event}</li>
          ))}
        </ol>
      )}
    </section>
  );
}

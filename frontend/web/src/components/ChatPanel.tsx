import { StatusMessage } from "./StatusMessage";

type ChatPanelProps = {
  question: string;
  answer: string;
  isStreaming: boolean;
  error: string | null;
  onQuestionChange: (value: string) => void;
  onSubmit: () => void;
};

export function ChatPanel({
  question,
  answer,
  isStreaming,
  error,
  onQuestionChange,
  onSubmit,
}: ChatPanelProps) {
  return (
    <section aria-label="Диалоговая система">
      <label>
        <span>Вопрос</span>
        <textarea
          aria-label="Вопрос"
          rows={4}
          value={question}
          placeholder="Что означает рост ВВП для рынка?"
          onChange={(event) => onQuestionChange(event.target.value)}
        />
      </label>
      <button type="button" onClick={onSubmit} disabled={isStreaming || !question.trim()}>
        {isStreaming ? "Streaming" : "Ask"}
      </button>
      {error ? (
        <div role="alert">
          <StatusMessage title="Ошибка запроса" detail={error} tone="error" />
        </div>
      ) : null}
      <article>{answer || "Ответ появится после отправки вопроса."}</article>
    </section>
  );
}

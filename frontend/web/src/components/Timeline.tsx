import type { ChatStreamEvent } from "../app/types";

type TimelineProps = {
  events: ChatStreamEvent[];
};

export function Timeline({ events }: TimelineProps) {
  return (
    <section aria-label="Pipeline timeline">
      <h2>Timeline</h2>
      {events.length === 0 ? (
        <p>События pipeline появятся во время ответа.</p>
      ) : (
        <ol>
          {events.map((event, index) => (
            <li key={`${event.event}-${index}`}>{event.event}</li>
          ))}
        </ol>
      )}
    </section>
  );
}

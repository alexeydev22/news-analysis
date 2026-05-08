import type { ImpactSummary, NewsDocument } from "../app/types";

type SourcesPanelProps = {
  sources: NewsDocument[];
  impactSummaries: ImpactSummary[];
};

function impactForSource(source: NewsDocument, impactSummaries: ImpactSummary[]) {
  return impactSummaries.find((summary) => summary.news_id === source.id);
}

export function SourcesPanel({ sources, impactSummaries }: SourcesPanelProps) {
  return (
    <aside aria-label="Источники анализа">
      <h2>Sources</h2>
      {sources.length === 0 ? (
        <p>Источники появятся после ответа.</p>
      ) : (
        <div>
          {sources.map((source) => {
            const impact = impactForSource(source, impactSummaries);
            return (
              <article key={source.id}>
                <h3>{source.title}</h3>
                <p>{source.source}</p>
                {typeof source.score === "number" ? <p>score {source.score.toFixed(2)}</p> : null}
                {impact ? (
                  <section>
                    <strong>{impact.impact}</strong>
                    <p>Impact: {impact.explanation}</p>
                  </section>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </aside>
  );
}

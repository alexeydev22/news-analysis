import type { ImpactSummary, NewsDocument } from "../app/types";
import { NewsDetails } from "./NewsDetails";

type SourcesPanelProps = {
  sources: NewsDocument[];
  impactSummaries: ImpactSummary[];
};

function impactForSource(source: NewsDocument, impactSummaries: ImpactSummary[]) {
  return impactSummaries.find((summary) => summary.news_id === source.id);
}

function localizeImpact(impact: string): string {
  if (impact === "positive") {
    return "позитивное";
  }
  if (impact === "negative") {
    return "негативное";
  }
  if (impact === "neutral") {
    return "нейтральное";
  }
  return impact;
}

export function SourcesPanel({ sources, impactSummaries }: SourcesPanelProps) {
  return (
    <aside aria-label="Источники анализа">
      <h2>Источники</h2>
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
                {typeof source.score === "number" ? (
                  <p>релевантность {source.score.toFixed(2)}</p>
                ) : null}
                {impact ? (
                  <section>
                    <strong>{localizeImpact(impact.impact)}</strong>
                    <p>Влияние: {impact.explanation}</p>
                  </section>
                ) : null}
                <NewsDetails title={source.title} text={source.text} />
              </article>
            );
          })}
        </div>
      )}
    </aside>
  );
}

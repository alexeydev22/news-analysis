import type { IndexNewsDatasetResponse, PreviewNewsResponse } from "../app/types";

type NewsPreviewProps = {
  preview: PreviewNewsResponse | null;
  indexResult: IndexNewsDatasetResponse | null;
};

export function NewsPreview({ preview, indexResult }: NewsPreviewProps) {
  return (
    <section>
      <h2>Набор данных</h2>
      {preview ? (
        <p>
          Предпросмотр: {preview.documents.length} / {preview.total_count}
        </p>
      ) : (
        <p>Предпросмотр пока пуст.</p>
      )}
      {preview?.documents.map((document) => (
        <article key={document.id}>
          <h3>{document.title}</h3>
          <p>{document.source}</p>
        </article>
      ))}
      {indexResult ? (
        <p>
          Проиндексировано {indexResult.indexed_count} из {indexResult.loaded_count} в{" "}
          {indexResult.collection_name}
        </p>
      ) : null}
    </section>
  );
}

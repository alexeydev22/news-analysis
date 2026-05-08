import type { IndexNewsDatasetResponse, PreviewNewsResponse } from "../app/types";

type NewsPreviewProps = {
  preview: PreviewNewsResponse | null;
  indexResult: IndexNewsDatasetResponse | null;
};

export function NewsPreview({ preview, indexResult }: NewsPreviewProps) {
  return (
    <section>
      <h2>Dataset</h2>
      {preview ? <p>Preview: {preview.documents.length} / {preview.total_count}</p> : <p>Preview is empty.</p>}
      {preview?.documents.map((document) => (
        <article key={document.id}>
          <h3>{document.title}</h3>
          <p>{document.source}</p>
        </article>
      ))}
      {indexResult ? (
        <p>
          Indexed {indexResult.indexed_count} of {indexResult.loaded_count} into{" "}
          {indexResult.collection_name}
        </p>
      ) : null}
    </section>
  );
}

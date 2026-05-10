import type { ActiveDataset, UploadedDataset } from "../app/types";

type DatasetUploadProps = {
  datasets: UploadedDataset[];
  activeDataset: ActiveDataset | null;
  isUploading: boolean;
  onUpload: (file: File) => void;
  onActivate: (datasetId: string) => void;
};

export function DatasetUpload({
  datasets,
  activeDataset,
  isUploading,
  onUpload,
  onActivate,
}: DatasetUploadProps) {
  return (
    <section className="datasetUpload" aria-label="CSV датасеты">
      <p className="datasetUploadStatus">
        {activeDataset ? `Активен: ${activeDataset.filename}` : "Активен demo CSV"}
      </p>

      <label>
        <span>CSV датасет</span>
        <input
          aria-label="CSV датасет"
          type="file"
          accept=".csv,text/csv"
          disabled={isUploading}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) {
              onUpload(file);
              event.target.value = "";
            }
          }}
        />
      </label>

      {datasets.length > 0 ? (
        <label>
          <span>Загруженные датасеты</span>
          <select
            aria-label="Загруженные датасеты"
            value={activeDataset?.dataset_id ?? ""}
            onChange={(event) => {
              if (event.target.value) {
                onActivate(event.target.value);
              }
            }}
          >
            {!activeDataset ? (
              <option value="" disabled>
                Выберите датасет
              </option>
            ) : null}
            {datasets.map((dataset) => (
              <option key={dataset.dataset_id} value={dataset.dataset_id}>
                {dataset.filename}
              </option>
            ))}
          </select>
        </label>
      ) : null}
    </section>
  );
}

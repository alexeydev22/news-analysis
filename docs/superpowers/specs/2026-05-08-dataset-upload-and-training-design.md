# Design: загрузка датасета и дообучение классификатора

## Цель

Довести курсовой проект до полного демонстрационного ML-цикла:

1. пользователь загружает CSV-датасет;
2. система валидирует и показывает preview;
3. выбранный датасет индексируется в Qdrant;
4. research pipeline обучает несколько классификаторов;
5. приложение запускается с обученными артефактами и позволяет переключать
   режимы анализа в чате.

Фича не должна превращать проект в MLOps-платформу. Training остается
воспроизводимым CLI-процессом, а production backend только использует готовые
артефакты.

## Scope

Входит:

- загрузка CSV через `news-service` API;
- выбор активного локального датасета из upload-volume;
- UI-контрол для загрузки CSV и отображения активного набора;
- CLI-конвертер внешних датасетов в две схемы:
  - application CSV: `id,title,text,source,published_at`;
  - training CSV: `article_id,text,impact,source,published_at`;
- обучение `tfidf-logreg`, `embedding-logreg`, `tiny-transformer-classifier`;
- сравнение моделей в `model_comparison.csv`;
- MLflow logging;
- `just`-команды для подготовки датасета, обучения, сравнения и запуска trained
  режима;
- документация и smoke-проверка.

Не входит:

- веб-интерфейс для запуска обучения;
- хранение загруженных датасетов в PostgreSQL;
- асинхронный training-service;
- скачивание полного FNSPID в репозиторий;
- автоматическая ручная разметка новостей.

## Датасеты

Основной большой датасет для retrieval и демонстрации масштабируемости:

- FNSPID: 15.7 млн финансовых новостей и 29.7 млн записей цен для 4 775
  компаний S&P 500 за 1999-2023 годы.
- Источники: Hugging Face paper `2402.06698`, GitHub
  `Zdong104/FNSPID_Financial_News_Dataset`, Hugging Face dataset
  `Zihan1004/FNSPID`.

Для supervised-обучения impact classifier использовать один из размеченных
источников:

- Financial News Dataset / FinSen: около 160 тыс. финансовых новостей,
  2007-2023, Apache 2.0;
- SEntFiN 1.0: размеченные financial headlines;
- `lwrf42/financial-sentiment-dataset`: Hugging Face sentiment dataset.

Практическая рекомендация: FNSPID использовать для большого retrieval-среза, а
FinSen или SEntFiN использовать для обучения `positive/neutral/negative`.

## Backend Design

### news-service

Добавить отдельный upload-порт без нарушения текущего `NewsSource`:

- `DatasetStorage` Protocol:
  - `save_upload(filename, bytes) -> UploadedDataset`;
  - `list_datasets() -> list[UploadedDataset]`;
  - `activate(dataset_id) -> ActiveDataset`;
  - `get_active_path() -> Path`.
- Infrastructure adapter: `LocalDatasetStorage`.
- Settings:
  - `NEWS_SERVICE_DATASET_UPLOAD_DIR=data/uploads`;
  - `NEWS_SERVICE_ACTIVE_DATASET_FILE=data/uploads/active_dataset.json`;
  - `NEWS_SERVICE_UPLOAD_MAX_BYTES`.

API:

- `POST /api/v1/news/datasets/upload` with `multipart/form-data`;
- `GET /api/v1/news/datasets`;
- `POST /api/v1/news/datasets/{dataset_id}/activate`;
- `GET /api/v1/news/datasets/active`.

Current preview/index endpoints should read the active uploaded dataset when it
exists, otherwise fallback to configured `NEWS_SERVICE_NEWS_DATASET_PATH`.

Validation:

- only `.csv`;
- size limit;
- required semantic columns via existing `CsvNewsSource`;
- clear `422` for invalid shape;
- no raw local paths in public errors.

### compose

Mount `../data` read-write for `news-service` and `news-worker`, because uploads
must be persisted in `data/uploads`.

## Frontend Design

Add a compact dataset control inside the existing left controls column:

- file input for CSV;
- upload button;
- active dataset name/status;
- list/select recent uploaded datasets;
- existing preview/index buttons continue to work on the active dataset.

Keep UI utilitarian. No training controls in UI; training remains a terminal
workflow to keep the course project maintainable.

## Research Pipeline Design

Add `tools/prepare_dataset.py`:

- input CSV path;
- output application CSV path;
- output training CSV path;
- column mapping flags:
  - `--id-column`;
  - `--title-column`;
  - `--text-column`;
  - `--source-column`;
  - `--published-at-column`;
  - `--label-column`;
  - optional score thresholds for weak labels.

For known formats, add presets:

- `--preset fin-sen`;
- `--preset sentfin`;
- `--preset fnspid`.

Training commands should stay in `research` package, but `justfile` gets
friendly wrappers:

- `just prepare-dataset INPUT`;
- `just train-baseline`;
- `just train-embedding`;
- `just train-transformer`;
- `just compare-models`;
- `just demo-up-trained`.

Expected artifacts:

- `artifacts/models/baseline/tfidf-logreg.joblib`;
- `artifacts/models/embedding/embedding-logreg.joblib`;
- `artifacts/models/transformer/tiny-transformer-classifier.joblib`;
- `artifacts/models/model_comparison.csv`.

## Analysis Service Design

Current `JoblibImpactClassifier` loads estimators and predicts labels. Extend it
only if needed to support:

- `predict_proba` confidence when estimator exposes probabilities;
- stable metadata with `artifact_path` and `source=joblib`.

No model training code should move into `analysis-service`.

## Error Handling

- Invalid upload format: `422`.
- Upload too large: `413`.
- Missing active dataset: fallback to configured demo dataset.
- Missing trained artifact with `ANALYSIS_USE_STATIC_CLASSIFIER=false`: existing
  unavailable model behavior remains correct.
- LLM unavailable: existing `dialog-service` unavailable behavior remains
  correct.

## Testing

Backend:

- `LocalDatasetStorage` unit tests;
- upload API tests for success, invalid extension, invalid CSV, activate/list;
- preview/index tests verifying active dataset is used;
- classifier tests for confidence from `predict_proba`.

Frontend:

- upload API client tests;
- App tests for upload success/error and active dataset display;
- existing preview/index/chat tests remain passing.

Research:

- `prepare_dataset.py` tests with fixture CSVs;
- validation that generated training CSV works with `research` CLI;
- comparison file contains all trained model rows when artifacts exist.

Verification:

```bash
uv run pytest packages apps -v
npm --prefix frontend/web test -- --run
docker compose -f deploy/compose.yaml config --quiet
uv run --project research python -m economic_news_research.cli validate --dataset data/raw/news_impact.csv
```

Full training can be manual because transformer/embedding modes may require
model downloads and more time.

## Acceptance Criteria

- User can upload CSV in UI and preview/index it without editing env files.
- CLI can convert at least one external financial dataset fixture into
  application and training schemas.
- `tfidf-logreg`, `embedding-logreg`, and `tiny-transformer-classifier` training
  commands produce artifacts under `artifacts/models`.
- `model_comparison.csv` is generated and documented.
- `demo-up-trained` starts app with `ANALYSIS_USE_STATIC_CLASSIFIER=false`.
- Final coursework docs mention the improved dataset/training workflow without
  overstating that full FNSPID is committed or automatically downloaded.

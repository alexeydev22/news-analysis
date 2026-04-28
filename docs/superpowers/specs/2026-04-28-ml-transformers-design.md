# Design: research-only transformer models

Дата: 2026-04-28

## 1. Цель

Этап `feature/ml-transformers` расширяет исследовательскую часть курсовой работы до полноценного сравнения минимум трех моделей для классификации экономического влияния новостей.

После этапа в `research` должны сравниваться:

1. `tfidf-logreg` - уже реализованный baseline.
2. `embedding-logreg` - легкая модель: sentence-transformer embeddings + Logistic Regression.
3. `tiny-transformer-classifier` - компактный trainable transformer-style classifier for coursework experiments.

Этап не добавляет backend-микросервисы, React UI, Qdrant или диалоговую LLM. Это отдельный research slice, который стабилизирует модельные артефакты и таблицы сравнения перед интеграцией в `analysis-service`.

## 2. Ограничения

- Не коммитить веса моделей, Hugging Face cache, MLflow runtime files или generated reports.
- Не требовать GPU.
- Сохранить возможность запуска на Mac с 16 GB RAM, но проектировать комфортно для 24-32 GB.
- Не усложнять код ради архитектуры: research modules могут быть проще production backend, но интерфейсы должны быть понятными.
- Не менять существующий `tfidf-logreg` behavior без необходимости.

## 3. Модели

### 3.1. Embedding classifier

`embedding-logreg` использует `sentence-transformers` для получения dense embeddings и `LogisticRegression` из scikit-learn для классификации.

Default embedding model:

```text
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Причина выбора: модель поддерживает multilingual texts, достаточно компактна для локального запуска и подходит для русско-английских новостных датасетов. Веса скачиваются в локальный Hugging Face cache, не в репозиторий.

### 3.2. Tiny transformer classifier

`tiny-transformer-classifier` в этом этапе реализуется как компактный trainable classifier через Hugging Face `transformers.Trainer` или прямой PyTorch training loop, если `Trainer` окажется слишком тяжелым для тестов.

Default model:

```text
cointegrated/rubert-tiny2
```

Если модель недоступна в окружении без сети, production training command должен явно сообщать, что нужен предварительно скачанный model cache. Unit tests не должны скачивать модель из сети: они используют маленький fake/adapter слой или monkeypatch, проверяющий orchestration, metrics и artifact export.

## 4. Общий интерфейс результатов

Существующий `BaselineTrainingResult` нужно обобщить без ломки текущего кода:

- общий result должен содержать `model_name`, `best_params`, `validation_metrics`, `test_metrics`, `estimator`;
- tracking/export должен уметь сохранить артефакты любой research-модели;
- `model_comparison.csv` должен поддерживать несколько строк и включать:
  - `model_name`;
  - validation/test accuracy;
  - validation/test macro F1;
  - inference time per sample;
  - best params JSON.

## 5. CLI

CLI расширяется так, чтобы research workflow был воспроизводимым:

```bash
uv run python -m economic_news_research.cli train-baseline
uv run python -m economic_news_research.cli train-embedding
uv run python -m economic_news_research.cli train-transformer
uv run python -m economic_news_research.cli compare-models
```

`train-baseline` остается совместимым. Новые команды пишут артефакты в ignored runtime folders under `artifacts/models` and `artifacts/mlflow`.

## 6. Testing strategy

Tests must remain deterministic and offline by default.

Required tests:

- result/export code supports multiple model names;
- embedding classifier can be tested with a deterministic fake embedder;
- transformer classifier orchestration can be tested without downloading model weights;
- CLI commands write expected artifacts into `tmp_path`;
- full test suite does not create root `mlflow.db`, `mlruns`, model caches, or untracked reports.

Network/model-download tests are out of scope for normal CI/local verification. Real model training can be run manually after placing the full dataset in `data/raw/news_impact.csv`.

## 7. Acceptance Criteria

- Research comparison includes 3 model rows: baseline, embedding classifier, tiny transformer classifier.
- `model_comparison.csv` contains metrics and inference time fields for all trained models.
- MLflow logs params, metrics and artifacts for new models.
- No heavy generated artifacts are committed.
- Existing checks pass:

```bash
uv run ruff check apps packages research
uv run ty check apps packages research
uv run pytest packages apps research/tests -v -W error
```


# Запуск режимов моделей и больших датасетов

Документ фиксирует, как развернуть стенд не только в demo-режиме, но и с
подключением обученных моделей, LLM-генератора и большого CSV-набора новостей.

## 1. Что уже поддерживает проект

В проекте есть три независимых переключателя.

| Область | Режимы | Как выбирается |
| --- | --- | --- |
| Анализ влияния | `tfidf-logreg`, `embedding-logreg`, `tiny-transformer-classifier` | Поле `analysis_model` в API и UI |
| Генерация ответа | `template`, `llm` | `DIALOG_GENERATOR_KIND` |
| Retrieval embeddings | статические embeddings, FastEmbed model | `RETRIEVAL_USE_STATIC_EMBEDDINGS` |

Важно: стандартный `docker compose` по умолчанию оставляет стабильный режим для
защиты:

```env
ANALYSIS_USE_STATIC_CLASSIFIER=true
RETRIEVAL_USE_STATIC_EMBEDDINGS=true
DIALOG_GENERATOR_KIND=template
```

В таком режиме стенд запускается быстро и воспроизводимо, но не использует
обученные артефакты моделей. Для полноценного запуска режимов анализа нужно
положить joblib-артефакты в `artifacts/models` и выключить static classifier.

## 2. Запуск стабильного demo-режима

```bash
just demo-up
just demo-smoke
```

После запуска открыть:

```text
http://localhost:5173
```

Проверка через UI:

1. Нажать `Предпросмотр CSV`.
2. Нажать `Индексировать CSV`.
3. Выбрать модель анализа.
4. Задать вопрос по экономическим новостям.
5. Проверить ответ, источники, score и timeline.

## 3. Запуск LLM-режима генерации

Сначала поднять OpenAI-compatible server, например `llama.cpp`:

```bash
llama-server \
  -m models/Qwen3-0.6B-Instruct-GGUF.gguf \
  --host 0.0.0.0 \
  --port 8080
```

Затем запустить compose с LLM-режимом:

```bash
DIALOG_GENERATOR_KIND=llm \
DIALOG_LLM_BASE_URL=http://host.docker.internal:8080 \
DIALOG_LLM_MODEL=Qwen3-0.6B-Instruct-GGUF \
docker compose -f deploy/compose.yaml up --build
```

Если `llama-server` недоступен, chat-сценарий ожидаемо упадет на этапе
генерации ответа. Для защиты без модели нужно вернуть `DIALOG_GENERATOR_KIND`
в `template`.

## 4. Подготовка обученных analysis-режимов

Внешний CSV сначала нужно привести к двум схемам. Для CSV с уже совместимыми
колонками:

```bash
just prepare-dataset path/to/external.csv
```

Для training CSV передайте label и, если нужно, названия внешних колонок:

```bash
just prepare-dataset path/to/external.csv \
  --title-column headline \
  --text-column body \
  --source-column publisher \
  --published-at-column date \
  --label-column sentiment \
  --positive-threshold 0.2 \
  --negative-threshold -0.2 \
  --limit 50000
```

Команда пишет:

- `data/raw/economic_news.csv` для preview/index в news app;
- `data/raw/news_impact.csv` для обучения research pipeline, если передан label.

Если нужны нестандартные output paths, запустите CLI напрямую:

```bash
uv run python tools/prepare_dataset.py path/to/external.csv \
  --app-output data/raw/economic_news.csv \
  --train-output data/raw/news_impact.csv \
  --title-column headline \
  --text-column body \
  --source-column publisher \
  --published-at-column date \
  --label-column sentiment \
  --positive-threshold 0.2 \
  --negative-threshold -0.2 \
  --limit 50000
```

Если `--id-column` не задан или такой колонки нет во входном CSV, CLI
сгенерирует стабильный `id`/`article_id` из `source`, `title` и `text`.
`--label-column` можно опустить, если нужен только CSV для news app.

Research pipeline ожидает размеченный CSV:

```text
data/raw/news_impact.csv
```

Минимальные колонки:

```text
article_id,text,impact,source,published_at
```

Допустимые значения `impact`:

```text
positive,neutral,negative
```

Команды обучения и сравнения:

```bash
just train-baseline
just train-embedding
just train-transformer
just compare-models
```

Ожидаемые артефакты:

```text
artifacts/models/baseline/tfidf-logreg.joblib
artifacts/models/embedding/embedding-logreg.joblib
artifacts/models/transformer/tiny-transformer-classifier.joblib
```

После этого можно запустить compose с обученными моделями:

```bash
just demo-up-trained
```

Краткий сценарий после обучения:

```bash
just compare-models
just demo-up-trained
```

В UI можно переключать обученные `tfidf-logreg`, `embedding-logreg` и
`tiny-transformer-classifier`. Если выбранный артефакт отсутствует,
`analysis-service` вернет управляемую ошибку недоступной модели, а не внутренний
traceback.

`analysis-service` монтирует `../artifacts` в `/app/artifacts`, поэтому
артефакты из локальной папки будут доступны внутри контейнера.

## 5. Запуск retrieval с реальными embeddings

По умолчанию включены статические embeddings, чтобы demo не скачивал модели.
Для более реалистичного поиска:

```bash
RETRIEVAL_USE_STATIC_EMBEDDINGS=false \
RETRIEVAL_EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 \
docker compose -f deploy/compose.yaml up --build
```

Первый запуск может скачать модель и занять больше времени. Для защиты лучше
проверить это заранее и не переключать режим в последний момент.

## 6. Большой датасет для индексации

Для большого retrieval-стенда лучше использовать FNSPID: Financial News and
Stock Price Integration Dataset. По описанию авторов, он содержит 15.7 млн
финансовых новостей и 29.7 млн записей цен для 4 775 компаний S&P 500 за
1999-2023 годы.

Ссылки:

- Hugging Face paper: <https://huggingface.co/papers/2402.06698>
- GitHub dataset repo: <https://github.com/Zdong104/FNSPID_Financial_News_Dataset>
- Hugging Face dataset: <https://huggingface.co/datasets/Zihan1004/FNSPID>

Для учебного стенда не нужно сразу индексировать все 15.7 млн записей. Более
практичный сценарий:

1. Скачать dataset локально.
2. Взять срез 50-200 тыс. новостей по одному периоду или нескольким тикерам.
3. Привести к CSV-схеме news-service.
4. Положить файл в `data/raw`.
5. Запустить compose с новым путем датасета.

Схема CSV для `news-service`:

```text
id,title,text,source,published_at
```

Также поддерживаются алиасы:

| Семантика | Поддерживаемые колонки |
| --- | --- |
| id | `id`, `news_id`, `article_id` |
| title | `title`, `headline` |
| text | `text`, `content`, `body`, `description` |
| source | `source`, `publisher` |
| published_at | `published_at`, `date`, `published` |

Запуск с большим CSV:

```bash
NEWS_SERVICE_NEWS_DATASET_PATH=data/raw/fnspid_sample.csv \
docker compose -f deploy/compose.yaml up --build
```

После старта:

```bash
curl http://localhost:8004/api/v1/news/preview?limit=5
```

Затем выполнить индексацию через UI или API. Для очень больших файлов лучше
начинать с ограниченного среза, потому что текущий `news-service` читает CSV
локально и индексирует batch через retrieval-service.

## 7. Датасеты для обучения классификатора

FNSPID хорошо подходит для большого retrieval и стресс-проверки индексации, но
для supervised-классификации нужен явный label `positive`, `neutral` или
`negative`. Если в выбранном срезе FNSPID нет готовой совместимой разметки,
нужно отдельно построить label:

- взять готовый sentiment score и преобразовать его в три класса;
- разметить новости по движению цены после публикации;
- использовать отдельный размеченный финансовый sentiment dataset.

Практичные источники для training/evaluation:

| Датасет | Когда использовать | Ссылка |
| --- | --- | --- |
| Financial News Dataset / FinSen | Средний по размеру набор: около 160 тыс. финансовых новостей, 2007-2023, Apache 2.0 | <https://www.kaggle.com/datasets/yogeshchary/financial-news-dataset/data> |
| SEntFiN 1.0 | Человеческая разметка financial headlines, удобно для sentiment/impact baseline | <https://huggingface.co/papers/2305.12257> |
| lwrf42 financial sentiment dataset | Готовые тексты с sentiment labels в Hugging Face формате | <https://huggingface.co/datasets/lwrf42/financial-sentiment-dataset> |

Рекомендация для курсовой: использовать FNSPID как большой retrieval dataset, а
для обучения impact classifier взять FinSen или SEntFiN и привести label к
`positive`, `neutral`, `negative`. Это лучше, чем пытаться вручную размечать
миллионы новостей.

## 8. Что еще желательно автоматизировать

После добавления CLI подготовки датасета основной production-like сценарий
выглядит так:

1. Подготовить внешний CSV через `just prepare-dataset path/to/external.csv`
   с нужными аргументами, например `--label-column sentiment`, или прямой
   запуск `tools/prepare_dataset.py` с явными колонками.
2. Обучить модели: `just train-baseline`, `just train-embedding`,
   `just train-transformer`.
3. Сравнить результаты: `just compare-models`.
4. Запустить стенд с обученными артефактами: `just demo-up-trained`.

Остается полезным отдельный будущий этап для управляемой индексации очень
больших CSV и документирования лимитов по памяти и времени для Mac.

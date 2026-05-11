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
2. Нажать `Индексировать CSV`. По умолчанию индексируется до 50 000 новостей
   батчами по 500 документов.
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

Артефакты моделей хранятся локально в `artifacts/models` и не коммитятся в git.
Это сделано намеренно: joblib-файлы зависят от окружения и могут быть крупными,
особенно для transformer-режима. После клонирования репозитория их нужно
обучить один раз на рабочей машине.

Для текущего учебного CSV из репозитория можно сразу подготовить training
dataset:

```bash
just prepare-demo-training
```

Эта команда сохраняет исходный `data/raw/economic_news.csv` для news-service и
создает `data/raw/news_impact.csv` для обучения.

## FNSPID importer

Основной сценарий:

```bash
just prepare-fnspid
just ml-full
just demo-up-trained
```

`just prepare-fnspid` скачивает ограниченный FNSPID news sample, сохраняет
`data/external/fnspid_sample.csv`, формирует `data/raw/economic_news.csv` и
`data/raw/news_impact.csv`. По умолчанию используется rule-based weak labeling:
метка `impact` вычисляется по экономическим маркерам в тексте новости.

Офлайн-сценарий для защиты:

```bash
just prepare-fnspid-local path/to/fnspid.csv --limit 50000
```

Если после дедупликации получилось меньше 50 000 строк, подготовьте исходный
файл с небольшим запасом и оставьте в `data/raw/economic_news.csv` первые
50 000 нормализованных строк. В Docker этот CSV виден news-service через volume
`../data/raw:/app/data/raw:ro`.

Команда пишет:

- `data/raw/economic_news.csv` для preview/index в news app;
- `data/raw/news_impact.csv` для обучения research pipeline.

Если во входном CSV нет подходящего идентификатора, importer сгенерирует
стабильный `id`/`article_id` из `source`, `title` и `text`.

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
just train-models
```

Эквивалентно можно выполнить шаги отдельно:

```bash
just train-baseline
just train-embedding
just train-transformer
just compare-models
```

Первый запуск `train-embedding` скачивает модель sentence-transformers, а
первый запуск `train-transformer` скачивает HuggingFace-модель
`cointegrated/rubert-tiny2`. Для этого нужен доступ в интернет. Cache
сохраняется в `artifacts/hf-cache` и затем монтируется в `analysis-service`.
В `just demo-up-trained` для HuggingFace включен offline режим, поэтому после
обучения compose использует локальный cache и не делает сетевые запросы при
инференсе.

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
just demo-up-trained
just trained-smoke
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
NEWS_SERVICE_NEWS_DATASET_PATH=data/raw/economic_news.csv \
docker compose -f deploy/compose.yaml up --build
```

После старта:

```bash
curl http://localhost:8004/api/v1/news/preview?limit=5
```

Затем выполнить индексацию через UI или API. Для очень больших файлов лучше
начинать с ограниченного среза, потому что текущий `news-service` читает CSV
локально и индексирует batch через retrieval-service.

## 7. FNSPID для обучения классификатора

Внешний датасет для проекта один: FNSPID. Для supervised-классификации нужен
явный label `positive`, `neutral` или `negative`. FNSPID importer строит label
внутри подготовки среза через rule-based weak labeling по экономическим маркерам
в тексте новости.

```bash
just prepare-fnspid-local path/to/fnspid.csv --limit 50000
```

## 8. Автоматизация ML-отчета

ML-отчет можно сформировать из интерфейса кнопкой `Сформировать ML-отчет`.
Frontend вызывает `analysis-service`, тот ставит Taskiq job в Redis, а
`analysis-worker` обучает три модели, сравнивает их и пишет JSON:

```text
reports/ml/model-report.json
```

CLI fallback для терминала:

1. Подготовить FNSPID sample через `just prepare-fnspid` или офлайн fallback
   `just prepare-fnspid-local path/to/fnspid.csv --limit 50000`.
2. Выполнить полный ML pipeline: `just ml-full`.
3. Запустить стенд с обученными артефактами: `just demo-up-trained`.

Для уже обученных артефактов достаточно:

```bash
just ml-report
```

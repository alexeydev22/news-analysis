# Demo Guide

## Цель проверки

Этот документ описывает, как самостоятельно проверить приложение перед защитой.
Проверка должна подтвердить, что проект запускается, индексирует русскоязычные
экономические новости и отвечает на вопросы в диалоговом интерфейсе.

## Быстрая проверка

Обновите `dev`:

```bash
git checkout dev
git pull
```

Запустите весь стек:

```bash
just demo-up
```

Во втором терминале запустите smoke-сценарий:

```bash
just demo-smoke
```

Успешный результат:

```text
ok: api-gateway health
ok: news-service health
ok: news preview returned 5 documents
ok: indexed 5 demo documents
ok: queued index job <uuid>
ok: chat stream emitted 8 events
ok: frontend returned HTML
ok: demo smoke passed
```

После проверки остановите контейнеры:

```bash
just demo-down
```

## Ручная проверка через UI

После `just demo-up` откройте:

```text
http://localhost:5173
```

Порядок действий:

1. Проверить блок датасетов. Если файл не загружался, должен отображаться
   активный demo CSV.
2. Нажать `Предпросмотр CSV`.
3. Убедиться, что появились русские экономические новости.
4. При необходимости загрузить собственный CSV через поле загрузки в панели
   управления. После успешной загрузки файл становится активным датасетом.
5. Нажать `Предпросмотр CSV` еще раз и убедиться, что предпросмотр идет уже по
   активному загруженному датасету.
6. Нажать `Индексировать CSV`.
7. Оставить модель анализа `tfidf-logreg`.
8. Ввести вопрос:

```text
Что означает рост ВВП и снижение инфляции для рынка?
```

9. Нажать `Спросить`.
10. Проверить результат:
   - появился русский ответ;
   - блок `Ход обработки` содержит этапы обработки;
   - справа отображаются источники;
   - у источников есть релевантность;
   - влияние отображается как `позитивное`, `нейтральное` или `негативное`.

## Проверка API без UI

Healthcheck gateway:

```bash
curl http://localhost:8000/health
```

Healthcheck news-service:

```bash
curl http://localhost:8004/health
```

Предпросмотр CSV:

```bash
curl 'http://localhost:8004/api/v1/news/preview?limit=3'
```

Индексация CSV:

```bash
curl -X POST http://localhost:8004/api/v1/news/index \
  -H 'Content-Type: application/json' \
  -d '{"limit": 5}'
```

Проверка SSE-чата:

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d '{"question":"Что значит рост ВВП?","analysis_model":"tfidf-logreg","limit":5}'
```

Ожидаемые SSE-события:

```text
chat_started
search_started
sources_found
analysis_started
analysis_completed
answer_started
answer_completed
done
```

## Проверка загрузки CSV через API

Загрузить CSV:

```bash
curl -X POST http://localhost:8004/api/v1/news/datasets/upload \
  -F 'file=@data/raw/economic_news.csv;type=text/csv'
```

Получить список загруженных датасетов:

```bash
curl http://localhost:8004/api/v1/news/datasets
```

Активировать загруженный датасет:

```bash
curl -X POST http://localhost:8004/api/v1/news/datasets/<dataset_id>/activate
```

Проверить активный датасет:

```bash
curl http://localhost:8004/api/v1/news/datasets/active
```

После активации обычные endpoints `preview`, `index` и `index/jobs` читают
активный загруженный CSV. Если активный файл отсутствует, сервис возвращается к
demo dataset из `NEWS_SERVICE_NEWS_DATASET_PATH`.

## Проверка фоновой индексации

Поставить задачу:

```bash
curl -X POST http://localhost:8004/api/v1/news/index/jobs \
  -H 'Content-Type: application/json' \
  -d '{"limit": 5}'
```

Ожидаемый ответ содержит:

```json
{
  "status": "queued",
  "job_id": "...",
  "events_channel": "news.index.events"
}
```

Это подтверждает, что `news-service` связан с `news-worker`, Taskiq и Redis.

## Проверка режимов анализа

В UI доступны режимы:

| Режим | Статус для demo | Назначение |
| --- | --- | --- |
| `tfidf-logreg` | работает после `just train-models` | Быстрая классификация влияния новости. |
| `embedding-logreg` | работает после `just train-models` | Классификация на embedding-признаках. |
| `tiny-transformer-classifier` | работает после `just train-models` | Классификация дообученной transformer-моделью. |

В обычном `just demo-up` режимы могут работать через static fallback. Для
проверки реальных обученных моделей используйте `just demo-up-trained`.

Для текущего учебного CSV из репозитория подготовьте размеченный training CSV:

```bash
just prepare-demo-training
```

Команда не перезаписывает `data/raw/economic_news.csv`; она создает
`data/raw/news_impact.csv` для research pipeline.

Подготовка FNSPID sample:

```bash
just prepare-fnspid
just ml-full
```

Если интернет недоступен, используйте заранее скачанный CSV:

```bash
just prepare-fnspid-local path/to/fnspid.csv --limit 50000
just ml-full
```

Если используется демо CSV, затем обучите и сравните модели:

```bash
just train-models
```

Эта команда создает локальные gitignored-артефакты:

```text
artifacts/models/baseline/tfidf-logreg.joblib
artifacts/models/embedding/embedding-logreg.joblib
artifacts/models/transformer/tiny-transformer-classifier.joblib
```

Первое обучение embedding и transformer режимов может скачать модели из
HuggingFace. Cache сохраняется в `artifacts/hf-cache` и используется
`analysis-service` при запуске `just demo-up-trained`. В trained compose для
HuggingFace включен offline режим, поэтому инференс идет из локального cache.

Запустите стенд с обученными артефактами:

```bash
just demo-up-trained
```

Быстрая API-проверка всех трех моделей:

```bash
just trained-smoke
```

Проверка всех режимов выполняется одинаково: выбрать режим в UI, задать один и
тот же вопрос, убедиться, что источники найдены, у каждой новости есть impact,
confidence и объяснение, а итоговый ответ сформирован по найденному контексту.
Если артефакт выбранной модели отсутствует, `analysis-service` возвращает
управляемую ошибку недоступной модели.

## Проверка ML-отчета во фронтенде

После подготовки training CSV и обученных артефактов откройте UI и нажмите
`Сформировать ML-отчет` в левой панели. Кнопка запускает backend job в
`analysis-service`, а тяжелая работа выполняется в `analysis-worker` через
Taskiq + Redis.

Ожидаемый результат:

- статус меняется с `в очереди` или `выполняется` на `готов`;
- появляется лучшая модель;
- отображаются accuracy, macro-F1 и время инференса;
- показываются распределение классов, confusion matrix и top features для
  `tfidf-logreg`.

Проверка без UI:

```bash
just ml-report
```

Команда пишет JSON, который читает frontend:

```text
reports/ml/model-report.json
```

## Проверка LLM-режима

По умолчанию `dialog-service` работает в `template`-режиме. Это сделано для
стабильного запуска без локальной языковой модели.

Чтобы проверить `llm`-режим:

1. Запустите OpenAI-compatible LLM server на порту `8080`, например:

```bash
llama-server -m models/Qwen3-0.6B-Instruct-Q8_0.gguf --host 0.0.0.0 --port 8080
```

2. Запустите compose с LLM-режимом:

```bash
DIALOG_GENERATOR_KIND=llm docker compose -f deploy/compose.yaml up --build
```

3. Проверьте UI или smoke:

```bash
uv run python tools/demo_smoke.py
```

Если LLM server не запущен, `llm`-режим ожидаемо завершится ошибкой на этапе
генерации ответа.

## Полная проверка разработки

Backend:

```bash
uv run ruff check apps packages research tools
uv run ty check apps packages research tools/demo_smoke.py
uv run pytest packages apps research/tests -q -W error
```

Frontend:

```bash
npm --prefix frontend/web test -- --run
npm --prefix frontend/web run lint
npm --prefix frontend/web run build
```

Docker Compose:

```bash
docker compose -f deploy/compose.yaml config --quiet
docker compose -f deploy/compose.yaml up -d --build
uv run python tools/demo_smoke.py
docker compose -f deploy/compose.yaml down
```

## Что делать при ошибке

- Если UI не открывается, проверить `docker compose -f deploy/compose.yaml ps`.
- Если чат не находит источники, нажать `Индексировать CSV` и повторить вопрос.
- Если `llm`-режим падает, проверить, что LLM server доступен на `localhost:8080`.
- Если `demo-smoke` падает на frontend, запустить backend-only проверку:

```bash
just demo-smoke-no-frontend
```

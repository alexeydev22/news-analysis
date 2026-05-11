# Topic Forecast Design

## Цель

Сделать экономический анализ заметно глубже: система должна не только анализировать отдельную новость, но и объединять похожие новости из индекса в темы, агрегировать их сигналы и формировать осторожный прогноз влияния по каждой теме.

Эта фаза должна дать видимый demo-result во frontend: пользователь видит темы, связанные новости, общий сигнал, прогноз, аргументы и риски.

## Scope

Входит в текущую итерацию:

- новые retrieval endpoints для чтения документов и соседей из Qdrant-backed индекса;
- новый topic forecast pipeline в `analysis-service`;
- JSON-хранилище последнего topic forecast;
- API для запуска/чтения topic forecast;
- frontend-панель topic forecast;
- документация demo-сценария.

Не входит в текущую итерацию:

- пересчет кластеров на каждый chat-вопрос;
- отдельный `forecast-service`;
- сложные online-кластеры с переобучением при каждом запросе;
- ценовой прогноз акции или инвестиционная рекомендация;
- персистентная история всех forecast-запусков.

## Архитектурное Решение

Выбран вариант C из обсуждения: Qdrant-neighborhood grouping.

Роли сервисов:

- `retrieval-service` остается владельцем Qdrant и vector store.
- `analysis-service` строит topic forecast как аналитический use case.
- `api-gateway` позже может использовать готовый forecast в chat flow, но в этой фазе не обязан пересчитывать forecast.
- frontend отображает готовый результат и кнопку формирования.

`analysis-service` не подключается к Qdrant напрямую. Вместо этого `retrieval-service` получает два endpoint:

- `GET /api/v1/documents?limit=...&source=...` - вернуть документы из текущего индекса;
- `POST /api/v1/neighbors` - вернуть ближайших соседей для списка document ids.

Так сохраняется микросервисная граница: Qdrant остается деталью retrieval-service.

## Retrieval Contracts

Новые contract-модели в `economic_news_contracts.retrieval`:

- `ListIndexedDocumentsResponse`;
- `IndexedNewsDocument`;
- `FindNeighborsRequest`;
- `FindNeighborsResponse`;
- `NewsNeighborGroup`;
- `NewsNeighbor`.

`IndexedNewsDocument` содержит:

- `id`;
- `title`;
- `text`;
- `source`;
- `published_at`;
- `metadata`.

`FindNeighborsRequest` содержит:

- `document_ids: list[str]`;
- `limit: int`, default `5`, max `20`;
- `source: str | None`.

`FindNeighborsResponse` возвращает группы соседей по каждому seed document:

- `document_id`;
- `neighbors`, каждый с `id`, `score`, `title`, `text`, `source`, `published_at`, `metadata`.

Если индекс пуст, endpoints возвращают пустые списки, а не ошибку.

## Retrieval Implementation

`VectorRepository` расширяется методами:

- `list_documents(limit: int, source: str | None) -> list[NewsDocument]`;
- `neighbors(document_ids: list[str], limit: int, source: str | None) -> dict[str, list[SearchResult]]`.

Для Qdrant implementation:

- `list_documents` использует scroll по collection payload;
- `neighbors` получает vector seed-точки и делает similarity query по каждой seed-точке;
- сам seed document исключается из neighbor list;
- при недоступности Qdrant используется существующая ошибка `RetrievalUnavailableError`.

Static/in-memory repository для тестов должен реализовать те же методы без Qdrant.

## Topic Forecast Model

Новые contract-модели в `economic_news_contracts.analysis`:

- `TopicForecastJobStatus`;
- `EnqueueTopicForecastJobResponse`;
- `TopicForecastJobResponse`;
- `TopicForecastNewsItemResponse`;
- `TopicForecastItemResponse`;
- `TopicForecastResponse`.

`TopicForecastItemResponse` содержит:

- `topic_id`;
- `title`;
- `summary`;
- `overall_impact: positive | neutral | negative`;
- `confidence: float | None`;
- `positive_count`;
- `neutral_count`;
- `negative_count`;
- `forecast`;
- `arguments: list[str]`;
- `risks: list[str]`;
- `news: list[TopicForecastNewsItemResponse]`.

`TopicForecastResponse` содержит:

- `generated_at`;
- `topics`;
- `metadata`.

## Topic Forecast Algorithm

Pipeline выполняется отдельной job, не на каждый chat-вопрос.

Шаги:

1. `analysis-service` получает документы из `retrieval-service`.
2. Для первых `max_seed_documents` документов запрашивает соседей.
3. Строит неориентированный graph:
   - node = news id;
   - edge = neighbor score выше порога, например `0.72`.
4. Находит connected components.
5. Для каждой компоненты:
   - ограничивает размер до `max_topic_size`;
   - прогоняет существующий impact classifier по текстам;
   - агрегирует `positive/neutral/negative`;
   - выбирает `overall_impact` большинством;
   - считает confidence как долю majority label с поправкой на средний confidence classifier-а;
   - строит title по самым частым значимым словам из заголовков;
   - строит summary, forecast, arguments и risks rule-based способом.

Правила forecast:

- majority `positive`: "вероятно положительное влияние при сохранении текущих условий";
- majority `negative`: "вероятно негативное влияние, если риски подтвердятся";
- majority `neutral`: "сигнал неоднозначный, требуется дополнительный контекст".

Обязательный disclaimer в forecast: это аналитическая оценка, не финансовая рекомендация.

## Analysis-Service API

Новые endpoints:

- `POST /api/v1/topic-forecast/jobs` - запустить построение forecast;
- `GET /api/v1/topic-forecast/jobs/{job_id}` - статус;
- `GET /api/v1/topic-forecast/latest` - последний готовый forecast или `null`.

Хранение:

- job status: `reports/topics/jobs/{job_id}.json`;
- latest report: `reports/topics/topic-forecast.json`.

Фоновое выполнение:

- использовать существующую Redis/Taskiq инфраструктуру `analysis-worker`;
- не добавлять RabbitMQ и новый broker.

## Frontend

В React UI добавляется панель `Тематический прогноз`.

Панель показывает:

- кнопку `Сформировать прогноз по темам`;
- статус job;
- список тем;
- для каждой темы:
  - название;
  - общий сигнал;
  - confidence;
  - распределение классов;
  - прогноз;
  - аргументы;
  - риски;
  - связанные новости.

Панель должна быть компактной и не ломать текущий chat UI. Лучше разместить ее в левой колонке ниже `ML-отчет` или отдельным блоком под основным чатом, если по ширине это читается лучше.

## Error Handling

Ожидаемые ошибки:

- retrieval-service недоступен;
- индекс пуст;
- Qdrant не содержит vectors для seed documents;
- analysis classifier недоступен;
- forecast job упала.

Для пустого индекса latest forecast должен показывать понятное состояние: "Недостаточно проиндексированных новостей для построения тем".

API не должен отдавать stack traces. Job status содержит короткое сообщение.

## Проверка

Минимальная проверка реализации:

- contract validation tests для новых retrieval/analysis DTO;
- retrieval-service tests для list documents и neighbors на fake repository;
- analysis-service tests для topic grouping и forecast aggregation;
- API tests для topic forecast jobs/latest;
- frontend tests для кнопки и отображения topic forecast;
- `docker compose -f deploy/compose.yaml config --quiet`;
- local smoke:
  1. подготовить FNSPID sample;
  2. проиндексировать новости;
  3. запустить topic forecast job;
  4. проверить `reports/topics/topic-forecast.json`;
  5. открыть frontend и увидеть темы.

## Влияние на Курсовую

Этап усиливает ML/NLP часть работы:

- появляется анализ группы новостей, а не только одной записи;
- используется vector neighborhood в Qdrant;
- классификатор impact применяется как часть агрегированного аналитического pipeline;
- результат можно показать на защите как "экономические темы и прогнозные сигналы".

Важно формулировать прогноз осторожно: система оценивает вероятное направление влияния по найденным новостям и не дает финансовых рекомендаций.

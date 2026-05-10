# ML Report UI Jobs Design

## Цель

Сделать ML-часть проекта видимой и управляемой из приложения: пользователь нажимает кнопку во фронтенде, backend запускает обучение и формирование отчета, UI показывает статус и готовые метрики моделей.

## Scope

В этой итерации добавляется один автоматизированный pipeline для текущего training CSV `data/raw/news_impact.csv`. Внешний большой датасет в документации остается один: FNSPID. Полный скачиватель FNSPID не добавляется, потому что датасет слишком большой для обязательного demo-сценария; проект документирует подготовку sample/limit и запускает ML pipeline на подготовленном CSV.

## Архитектура

`analysis-service` получает новые endpoints:

- `POST /api/v1/ml-report/jobs` запускает job.
- `GET /api/v1/ml-report/jobs/{job_id}` возвращает статус.
- `GET /api/v1/ml-report/latest` возвращает последний готовый отчет или `null`.

Тяжелая работа выполняется в `analysis-worker` через Taskiq + Redis. Worker запускает research pipeline: обучение трех моделей, сравнение моделей, генерация JSON-отчета. Состояние job и latest report хранятся в локальном JSON-хранилище под `reports/ml`, чтобы сервис и worker видели один и тот же результат через Docker volume.

## Формат отчета

`reports/ml/model-report.json` содержит:

- сведения о датасете: путь, число строк, распределение `positive/neutral/negative`;
- список моделей с `accuracy`, `macro_f1`, `inference_seconds_per_sample`;
- лучшую модель по `test_macro_f1`;
- confusion matrix по каждой модели;
- top features для `tfidf-logreg`.

## Frontend

В React UI добавляется секция `ML-отчет` в левую панель. Она содержит кнопку `Сформировать ML-отчет`, статус выполнения, таблицу сравнения моделей, лучшую модель, распределение классов, confusion matrix и top features. Если отчета нет, показывается понятное пустое состояние.

## Ошибки

Если training CSV отсутствует или pipeline падает, job получает статус `failed` и короткое сообщение ошибки. API не отдает внутренние stack traces. UI показывает человекочитаемое сообщение.

## Проверка

Минимальная проверка:

- unit tests для генерации отчета;
- API tests для endpoints analysis-service;
- frontend tests для кнопки и отображения отчета;
- `docker compose -f deploy/compose.yaml config --quiet`;
- локальный smoke: создать отчет через API и прочитать latest.

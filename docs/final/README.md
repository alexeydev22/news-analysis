# Финальные материалы для сдачи

В папке лежат готовые артефакты, которые можно использовать для защиты:

- `coursework-explanatory-note.docx` — пояснительная записка;
- `coursework-defense-presentation.pptx` — презентация на 12 слайдов;
- `assets/architecture-diagram.png` — архитектурная схема;
- `assets/ui-demo-screenshot.png` — иллюстрация demo-интерфейса;
- `qa/` — технические файлы проверки артефактов.

Материалы раскрывают как ML/NLP-часть проекта, так и инженерную реализацию:
retrieval, загрузку CSV через интерфейс, активный загруженный датасет,
классификацию влияния, обучение режимов моделей, LLM-адаптер, MLflow,
микросервисную DDD-архитектуру, асинхронные сервисы, SSE, фоновые задачи и
Docker Compose запуск.

Проверка приложения перед защитой:

```bash
just demo-up
just demo-smoke
just demo-down
```

Подробная инструкция по запуску LLM-режима, обученных analysis-режимов и
большого датасета описана в
[docs/deployment/model-modes-and-large-datasets.md](../deployment/model-modes-and-large-datasets.md).

Ручная проверка:

1. Открыть `http://localhost:5173`.
2. При необходимости загрузить CSV в блоке датасетов и убедиться, что он стал
   активным.
3. Нажать `Предпросмотр CSV`.
4. Нажать `Индексировать CSV`.
5. Задать вопрос: `Что означает рост ВВП и снижение инфляции для рынка?`
6. Проверить, что отображаются ответ, источники, impact, confidence и ход
   обработки.

Проверка обученных моделей:

```bash
just prepare-dataset path/to/external.csv --label-column sentiment
just train-baseline
just train-embedding
just train-transformer
just compare-models
just demo-up-trained
```

После запуска `just demo-up-trained` нужно последовательно выбрать в UI режимы
`tfidf-logreg`, `embedding-logreg` и `tiny-transformer-classifier`, задать один и
тот же вопрос и проверить наличие найденных источников, класса влияния,
confidence score и итогового ответа.

Примечание: `.docx` и `.pptx` собраны из материалов в `docs/coursework` и
`docs/presentation`. В финальные файлы внесены данные студента:
Прудиев Алексей Сергеевич, группа ПМ23-4, Финансовый университет при
Правительстве РФ. Перед сдачей остается заполнить ФИО руководителя и, при
необходимости, название дисциплины.

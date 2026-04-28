# Economic News Dialog System

Локальная микросервисная диалоговая система для анализа экономических новостей.

## Тема курсовой работы

Разработка автоматической диалоговой системы на основе языковой модели для анализа экономических новостей.

## Архитектура

Проект строится как monorepo:

- `apps/` — backend-микросервисы;
- `packages/framework` — общий технический foundation;
- `packages/contracts` — общие DTO и event schemas;
- `frontend/web` — React UI;
- `research/` — notebooks, training scripts, reports;
- `docs/` — пояснительная записка и презентация;
- `deploy/` — Docker Compose и Dockerfiles.

## Ветки

- `master` — стабильная основная ветка;
- `dev` — ветка разработки и интеграционного тестирования;
- `feature/*` — ветки отдельных этапов.

## Commit style

Коммиты пишутся на русском языке с conventional prefix:

- `feat: добавить ...`
- `fix: исправить ...`
- `refactor: упростить ...`
- `test: добавить ...`
- `docs: описать ...`
- `chore: настроить ...`

## Локальный запуск foundation

```bash
just test
just compose-up
```

API Gateway healthcheck:

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:

```json
{"service":"api-gateway","status":"ok"}
```

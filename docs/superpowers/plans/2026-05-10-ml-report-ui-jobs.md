# ML Report UI Jobs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a frontend button that launches an automated ML training/report job and renders the resulting model report in the application.

**Architecture:** Keep ML training inside `analysis-worker` using Taskiq + Redis, with `analysis-service` exposing job/status/latest endpoints. Store job state and the latest report as JSON files under `reports/ml`, shared by service and worker through Docker volumes.

**Tech Stack:** FastAPI, Dishka, Taskiq, Redis, pandas, scikit-learn, joblib, React, Vitest, Docker Compose, Justfile.

---

## File Map

- Create `research/scripts/economic_news_research/reporting.py` for report generation.
- Modify `research/scripts/economic_news_research/cli.py` to expose `ml-report`.
- Create tests in `research/tests/test_reporting.py`.
- Extend `packages/contracts/src/economic_news_contracts/analysis.py` with ML report DTOs.
- Add analysis-service use cases, storage, queue, worker and endpoints.
- Add frontend API/types/component/tests for ML report UI.
- Update `deploy/compose.yaml`, nginx config, `justfile`, and docs.

## Tasks

- [ ] Add research report builder and tests.
- [ ] Add CLI/Justfile automation.
- [ ] Add analysis-service ML report contracts, storage and endpoints.
- [ ] Add analysis-worker Taskiq job.
- [ ] Add frontend ML report panel and API tests.
- [ ] Update Docker Compose, docs and smoke verification.

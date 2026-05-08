# E2E Demo Scenario Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible local demo scenario for coursework defense.

**Architecture:** Demo assets live outside service internals. A standard-library Python smoke script calls existing HTTP endpoints and parses SSE events. Just commands and README wire the flow for local use.

**Tech Stack:** Python standard library, pytest, Docker Compose, Just, existing FastAPI/SSE endpoints, React frontend.

---

### Task 1: Demo Dataset

**Files:**
- Create: `data/raw/economic_news.csv`

- [ ] **Step 1: Add a small stable CSV dataset**

Use columns accepted by `news-service`: `title`, `text`, `source`, `published_at`, `impact`.

- [ ] **Step 2: Verify preview can parse the dataset through existing tests or smoke script**

Run focused news-service tests after the script exists.

### Task 2: Smoke Script

**Files:**
- Create: `tools/demo_smoke.py`
- Test: `packages/framework/tests/test_demo_smoke.py`

- [ ] **Step 1: Write failing tests for URL joining and SSE parsing**

Tests should import the script by path and verify helper behavior without Docker.

- [ ] **Step 2: Implement minimal helpers and CLI**

The script should check health, preview, enqueue indexing, chat stream, and optional frontend HTML.

- [ ] **Step 3: Run focused tests**

Run `uv run pytest packages/framework/tests/test_demo_smoke.py -q -W error`.

### Task 3: Commands And Documentation

**Files:**
- Modify: `justfile`
- Modify: `README.md`

- [ ] **Step 1: Add demo commands**

Add `demo-up`, `demo-smoke`, and `demo-down`.

- [ ] **Step 2: Document defense-ready demo flow**

Add commands and expected behavior to README.

### Task 4: Verification And PR

**Files:**
- Repository-wide checks only.

- [ ] **Step 1: Run full verification**

Run backend tests, frontend tests/build, compose config, and relevant Docker builds.

- [ ] **Step 2: Commit, push, and open PR**

Use Russian conventional commit message.

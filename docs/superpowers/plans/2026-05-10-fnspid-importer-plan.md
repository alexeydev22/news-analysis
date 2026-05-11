# FNSPID Importer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an automated FNSPID importer that downloads or reads a limited news sample, prepares `economic_news.csv` and `news_impact.csv`, and weak-labels impact classes.

**Architecture:** Keep the importer as a focused CLI tool in `tools/prepare_fnspid.py`. Reuse the existing CSV schema conventions from `tools/prepare_dataset.py`, but do not change the existing generic importer unless a tiny helper export is needed. The importer writes ignored data files only and remains independent from training, retrieval, and UI.

**Tech Stack:** Python 3.13, pandas, existing `justfile`, pytest, ruff, ty.

---

## File Structure

- Create `tools/prepare_fnspid.py`: FNSPID source loading, column detection, rule-based weak labeling, output writing, CLI.
- Create `tests/test_prepare_fnspid.py`: unit and CLI-level tests for local FNSPID-like CSV preparation.
- Modify `justfile`: add `prepare-fnspid` and `prepare-fnspid-local`.
- Modify `docs/deployment/model-modes-and-large-datasets.md`: replace manual FNSPID sample instructions with automated importer commands.
- Modify `docs/demo.md`: add the simple demo command sequence with `just prepare-fnspid`.
- Modify `research/README.md`: mention FNSPID importer before `train-models` and `ml-report`.

## Task 1: Rule-Based Weak Labeling

**Files:**
- Create: `tools/prepare_fnspid.py`
- Test: `tests/test_prepare_fnspid.py`

- [ ] **Step 1: Write failing tests for text labeling**

Add `tests/test_prepare_fnspid.py`:

```python
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.prepare_fnspid import label_impact_from_text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Company profit rises and outlook improves after strong demand", "positive"),
        ("Shares fall as losses widen and demand weakens", "negative"),
        ("The company announced a board meeting on Monday", "neutral"),
        ("Revenue rises but inflation risks increase and demand weakens", "neutral"),
    ],
)
def test_label_impact_from_text_uses_economic_markers(text: str, expected: str) -> None:
    assert label_impact_from_text(text) == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_prepare_fnspid.py::test_label_impact_from_text_uses_economic_markers -v
```

Expected: FAIL with `ModuleNotFoundError` or missing `label_impact_from_text`.

- [ ] **Step 3: Implement minimal labeler**

Create `tools/prepare_fnspid.py`:

```python
from __future__ import annotations

import argparse
import hashlib
from collections import Counter
from pathlib import Path

import pandas as pd

FNSPID_SOURCE_URL = (
    "https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/"
    "Stock_news/nasdaq_exteral_data.csv"
)

APP_COLUMNS = ["id", "title", "text", "source", "published_at"]
TRAIN_COLUMNS = ["article_id", "text", "impact", "source", "published_at"]

POSITIVE_MARKERS = frozenset(
    {
        "beat",
        "beats",
        "gain",
        "gains",
        "grow",
        "grows",
        "growth",
        "improve",
        "improves",
        "profit",
        "profits",
        "raise",
        "raises",
        "rise",
        "rises",
        "strong demand",
        "upgrade",
        "upgrades",
    },
)
NEGATIVE_MARKERS = frozenset(
    {
        "decline",
        "declines",
        "drop",
        "drops",
        "fall",
        "falls",
        "inflation risks",
        "loss",
        "losses",
        "recession",
        "risk",
        "risks",
        "slowdown",
        "weak demand",
        "weaken",
        "weakens",
    },
)


def label_impact_from_text(text: str) -> str:
    normalized_text = text.lower()
    positive_score = sum(marker in normalized_text for marker in POSITIVE_MARKERS)
    negative_score = sum(marker in normalized_text for marker in NEGATIVE_MARKERS)

    if positive_score > negative_score:
        return "positive"
    if negative_score > positive_score:
        return "negative"
    return "neutral"
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_prepare_fnspid.py::test_label_impact_from_text_uses_economic_markers -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/prepare_fnspid.py tests/test_prepare_fnspid.py
git commit -m "feat: добавить weak labeling для FNSPID"
```

## Task 2: FNSPID Frame Normalization

**Files:**
- Modify: `tools/prepare_fnspid.py`
- Modify: `tests/test_prepare_fnspid.py`

- [ ] **Step 1: Write failing test for FNSPID-like CSV preparation**

Append to `tests/test_prepare_fnspid.py`:

```python
from tools.prepare_fnspid import prepare_fnspid


def test_prepare_fnspid_writes_news_and_training_csv(tmp_path: Path) -> None:
    source_path = tmp_path / "fnspid.csv"
    news_output_path = tmp_path / "economic_news.csv"
    training_output_path = tmp_path / "news_impact.csv"
    cache_path = tmp_path / "fnspid_sample.csv"
    pd.DataFrame(
        {
            "Date": ["2026-05-01", "2026-05-02", "2026-05-03"],
            "Article_title": ["Profit rises", "Losses widen", "Board meeting"],
            "Article": [
                "Company profit rises after strong demand",
                "Shares fall as losses widen",
                "The company announced a board meeting",
            ],
            "Stock_symbol": ["AAPL", "MSFT", "JPM"],
            "Url": ["https://example.com/1", "https://example.com/2", "https://example.com/3"],
        },
    ).to_csv(source_path, index=False)

    summary = prepare_fnspid(
        source=source_path,
        cache_path=cache_path,
        news_output_path=news_output_path,
        training_output_path=training_output_path,
        limit=3,
        max_text_chars=200,
    )

    news_frame = pd.read_csv(news_output_path)
    training_frame = pd.read_csv(training_output_path)
    cached_frame = pd.read_csv(cache_path)

    assert summary.row_count == 3
    assert summary.class_distribution == {"negative": 1, "neutral": 1, "positive": 1}
    assert news_frame.columns.to_list() == ["id", "title", "text", "source", "published_at"]
    assert training_frame.columns.to_list() == [
        "article_id",
        "text",
        "impact",
        "source",
        "published_at",
    ]
    assert training_frame["impact"].to_list() == ["positive", "negative", "neutral"]
    assert cached_frame.shape[0] == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_prepare_fnspid.py::test_prepare_fnspid_writes_news_and_training_csv -v
```

Expected: FAIL because `prepare_fnspid` is missing.

- [ ] **Step 3: Implement normalization and writer**

Extend `tools/prepare_fnspid.py`:

```python
from dataclasses import dataclass

TEXT_COLUMNS = ("Article", "article", "text", "body", "content", "description")
TITLE_COLUMNS = ("Article_title", "title", "headline", "Title")
DATE_COLUMNS = ("Date", "date", "published_at", "published", "time")
SOURCE_COLUMNS = ("source", "publisher", "Stock_symbol", "ticker", "symbol")
ID_COLUMNS = ("id", "article_id", "Url", "url", "link")


@dataclass(frozen=True)
class FNSPIDPrepareSummary:
    row_count: int
    class_distribution: dict[str, int]
    news_output_path: Path
    training_output_path: Path
    cache_path: Path


def stable_id(*parts: str) -> str:
    digest = hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


def first_existing_column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    lowered = {column.lower(): column for column in frame.columns}
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return None


def require_column(frame: pd.DataFrame, candidates: tuple[str, ...], label: str) -> str:
    column = first_existing_column(frame, candidates)
    if column is None:
        raise ValueError(f"FNSPID CSV does not contain a {label} column")
    return column


def normalize_text(values: pd.Series, *, max_chars: int) -> pd.Series:
    normalized = values.fillna("").astype(str).str.strip()
    normalized = normalized[normalized.ne("")]
    return normalized.str.slice(0, max_chars)


def normalize_dates(values: pd.Series) -> pd.Series:
    dates = pd.to_datetime(values, errors="coerce", format="mixed", utc=True)
    return dates.dt.strftime("%Y-%m-%dT%H:%M:%SZ").fillna("1970-01-01T00:00:00Z")


def build_frames(frame: pd.DataFrame, *, max_text_chars: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    title_column = require_column(frame, TITLE_COLUMNS, "title")
    text_column = require_column(frame, TEXT_COLUMNS, "text")
    date_column = first_existing_column(frame, DATE_COLUMNS)
    source_column = first_existing_column(frame, SOURCE_COLUMNS)
    id_column = first_existing_column(frame, ID_COLUMNS)

    title = normalize_text(frame[title_column], max_chars=300)
    text = normalize_text(frame[text_column], max_chars=max_text_chars)
    valid_index = title.index.intersection(text.index)
    title = title.loc[valid_index]
    text = text.loc[valid_index]
    source = (
        frame.loc[valid_index, source_column].fillna("FNSPID").astype(str).str.strip()
        if source_column is not None
        else pd.Series("FNSPID", index=valid_index)
    )
    published_at = (
        normalize_dates(frame.loc[valid_index, date_column])
        if date_column is not None
        else pd.Series("1970-01-01T00:00:00Z", index=valid_index)
    )

    if id_column is not None:
        ids = frame.loc[valid_index, id_column].fillna("").astype(str).str.strip()
        ids = ids.where(ids.ne(""), other=pd.Series(index=valid_index, dtype=str))
    else:
        ids = pd.Series(index=valid_index, dtype=str)

    ids = ids.fillna(
        pd.Series(
            [
                stable_id(source_value, title_value, text_value)
                for source_value, title_value, text_value in zip(source, title, text, strict=True)
            ],
            index=valid_index,
        ),
    )

    app_frame = pd.DataFrame(
        {
            "id": ids,
            "title": title,
            "text": text,
            "source": source.where(source.ne(""), "FNSPID"),
            "published_at": published_at,
        },
    ).drop_duplicates(subset=["id"])
    impact = app_frame["text"].map(label_impact_from_text)
    training_frame = pd.DataFrame(
        {
            "article_id": app_frame["id"],
            "text": app_frame["text"],
            "impact": impact,
            "source": app_frame["source"],
            "published_at": app_frame["published_at"],
        },
    )
    return app_frame, training_frame


def read_limited_csv(source: Path | str, *, limit: int) -> pd.DataFrame:
    chunks: list[pd.DataFrame] = []
    rows_left = limit
    for chunk in pd.read_csv(source, chunksize=min(5000, limit)):
        if rows_left <= 0:
            break
        selected = chunk.head(rows_left)
        chunks.append(selected)
        rows_left -= len(selected)
    if not chunks:
        raise ValueError("FNSPID source did not contain any rows")
    return pd.concat(chunks, ignore_index=True)


def write_csv(frame: pd.DataFrame, output_path: Path, columns: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.loc[:, columns].to_csv(output_path, index=False)


def prepare_fnspid(
    *,
    source: Path | str,
    cache_path: Path,
    news_output_path: Path,
    training_output_path: Path,
    limit: int,
    max_text_chars: int,
) -> FNSPIDPrepareSummary:
    raw_frame = read_limited_csv(source, limit=limit)
    app_frame, training_frame = build_frames(raw_frame, max_text_chars=max_text_chars)
    if app_frame.empty:
        raise ValueError("FNSPID sample is empty after filtering")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    raw_frame.head(len(app_frame)).to_csv(cache_path, index=False)
    write_csv(app_frame, news_output_path, APP_COLUMNS)
    write_csv(training_frame, training_output_path, TRAIN_COLUMNS)

    distribution = dict(sorted(Counter(training_frame["impact"]).items()))
    return FNSPIDPrepareSummary(
        row_count=len(app_frame),
        class_distribution=distribution,
        news_output_path=news_output_path,
        training_output_path=training_output_path,
        cache_path=cache_path,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_prepare_fnspid.py::test_prepare_fnspid_writes_news_and_training_csv -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/prepare_fnspid.py tests/test_prepare_fnspid.py
git commit -m "feat: подготовить FNSPID CSV"
```

## Task 3: CLI and Justfile Commands

**Files:**
- Modify: `tools/prepare_fnspid.py`
- Modify: `tests/test_prepare_fnspid.py`
- Modify: `justfile`

- [ ] **Step 1: Write failing CLI test**

Append to `tests/test_prepare_fnspid.py`:

```python
from tools.prepare_fnspid import main


def test_prepare_fnspid_cli_writes_outputs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source_path = tmp_path / "fnspid.csv"
    pd.DataFrame(
        {
            "Date": ["2026-05-01"],
            "Article_title": ["Profit rises"],
            "Article": ["Company profit rises after strong demand"],
        },
    ).to_csv(source_path, index=False)

    main(
        [
            "--local-file",
            str(source_path),
            "--limit",
            "1",
            "--cache-path",
            str(tmp_path / "cache.csv"),
            "--output-news",
            str(tmp_path / "news.csv"),
            "--output-training",
            str(tmp_path / "training.csv"),
        ],
    )

    captured = capsys.readouterr()
    assert "rows=1" in captured.out
    assert "positive=1" in captured.out
    assert (tmp_path / "news.csv").exists()
    assert (tmp_path / "training.csv").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_prepare_fnspid.py::test_prepare_fnspid_cli_writes_outputs -v
```

Expected: FAIL because `main` does not accept argv or CLI is missing.

- [ ] **Step 3: Implement CLI parser**

Extend `tools/prepare_fnspid.py`:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download and prepare a limited FNSPID news sample.")
    parser.add_argument("--local-file", type=Path)
    parser.add_argument("--source-url", default=FNSPID_SOURCE_URL)
    parser.add_argument("--limit", type=int, default=50000)
    parser.add_argument("--cache-path", type=Path, default=Path("data/external/fnspid_sample.csv"))
    parser.add_argument("--output-news", type=Path, default=Path("data/raw/economic_news.csv"))
    parser.add_argument("--output-training", type=Path, default=Path("data/raw/news_impact.csv"))
    parser.add_argument("--max-text-chars", type=int, default=4000)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    source = args.local_file if args.local_file is not None else args.source_url
    try:
        summary = prepare_fnspid(
            source=source,
            cache_path=args.cache_path,
            news_output_path=args.output_news,
            training_output_path=args.output_training,
            limit=args.limit,
            max_text_chars=args.max_text_chars,
        )
    except Exception as error:
        raise SystemExit(
            "Failed to prepare FNSPID sample. "
            "Use --local-file path/to/fnspid.csv if the public source is unavailable. "
            f"Cause: {error}",
        ) from error

    distribution = " ".join(
        f"{label}={count}" for label, count in summary.class_distribution.items()
    )
    print(
        f"rows={summary.row_count} {distribution} "
        f"news_output={summary.news_output_path} "
        f"training_output={summary.training_output_path} "
        f"cache={summary.cache_path}",
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Add just commands**

Modify `justfile` near `prepare-dataset`:

```make
prepare-fnspid:
    uv run python tools/prepare_fnspid.py

prepare-fnspid-local input +args='':
    uv run python tools/prepare_fnspid.py --local-file {{input}} {{args}}
```

- [ ] **Step 5: Run CLI and justfile checks**

Run:

```bash
uv run pytest tests/test_prepare_fnspid.py::test_prepare_fnspid_cli_writes_outputs -v
just --list | rg "prepare-fnspid"
```

Expected: test PASS and both just commands listed.

- [ ] **Step 6: Commit**

```bash
git add tools/prepare_fnspid.py tests/test_prepare_fnspid.py justfile
git commit -m "feat: добавить команды импорта FNSPID"
```

## Task 4: Documentation Update

**Files:**
- Modify: `docs/deployment/model-modes-and-large-datasets.md`
- Modify: `docs/demo.md`
- Modify: `research/README.md`

- [ ] **Step 1: Update deployment docs**

In `docs/deployment/model-modes-and-large-datasets.md`, replace manual FNSPID preparation examples with:

```markdown
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
```

- [ ] **Step 2: Update demo docs**

In `docs/demo.md`, add:

```markdown
Подготовка FNSPID sample:

```bash
just prepare-fnspid
just ml-full
```

Если интернет недоступен, используйте заранее скачанный CSV:

```bash
just prepare-fnspid-local path/to/fnspid.csv --limit 50000
```
```

- [ ] **Step 3: Update research README**

In `research/README.md`, add before training commands:

```markdown
Для автоматической подготовки FNSPID:

```bash
just prepare-fnspid
```

Команда создает `data/raw/news_impact.csv` с rule-based weak labels.
```

- [ ] **Step 4: Verify docs do not reintroduce generic dataset language**

Run:

```bash
rg "path/to/external.csv|--label-column sentiment" docs/deployment/model-modes-and-large-datasets.md docs/demo.md docs/coursework docs/final/README.md
```

Expected: no matches.

- [ ] **Step 5: Commit**

```bash
git add docs/deployment/model-modes-and-large-datasets.md docs/demo.md research/README.md
git commit -m "docs: обновить сценарий FNSPID"
```

## Task 5: Final Verification

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run focused tests**

```bash
uv run pytest tests/test_prepare_fnspid.py tests/test_prepare_dataset.py -v
```

Expected: PASS.

- [ ] **Step 2: Run lint and type checks**

```bash
uv run ruff check tools/prepare_fnspid.py tests/test_prepare_fnspid.py
uv run ty check tools/prepare_fnspid.py
```

Expected: both pass.

- [ ] **Step 3: Run local importer smoke**

Create a temp FNSPID-like CSV and run the just command:

```bash
uv run python - <<'PY'
from pathlib import Path
import pandas as pd

path = Path("/tmp/fnspid_smoke.csv")
pd.DataFrame(
    {
        "Date": ["2026-05-01", "2026-05-02", "2026-05-03"],
        "Article_title": ["Profit rises", "Losses widen", "Board meeting"],
        "Article": [
            "Company profit rises after strong demand",
            "Shares fall as losses widen",
            "The company announced a board meeting",
        ],
    },
).to_csv(path, index=False)
print(path)
PY
just prepare-fnspid-local /tmp/fnspid_smoke.csv --limit 3
```

Expected: output contains `rows=3`, and the generated files exist:

```bash
test -f data/raw/economic_news.csv
test -f data/raw/news_impact.csv
```

- [ ] **Step 4: Run report smoke**

```bash
just ml-report
```

Expected: `model_report_path=reports/ml/model-report.json`.

- [ ] **Step 5: Check git status**

```bash
git status --short
```

Expected: only intended changed files are tracked. Generated `data/raw/*`, `data/external/*`, and `reports/*` remain ignored.

- [ ] **Step 6: Final commit if needed**

If any verification-only fixes were needed:

```bash
git add <changed-files>
git commit -m "fix: стабилизировать импорт FNSPID"
```

## Self-Review

- Spec coverage: importer download/local fallback, limited sample, two output CSV files, weak labels, docs, and tests are covered.
- Scope check: topic clustering and forecast remain documented as the next phase and are not implemented here.
- Type consistency: public implementation names are `prepare_fnspid`, `label_impact_from_text`, `FNSPIDPrepareSummary`, `prepare-fnspid`, and `prepare-fnspid-local`.
- No required implementation step depends on network; remote download is implemented, but tests use local CSV fixtures.

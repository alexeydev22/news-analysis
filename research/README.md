# ML Research

This folder contains reproducible research code for economic news impact classification.

## Dataset

Place the full dataset at:

```text
data/raw/news_impact.csv
```

Required columns:

```text
article_id,text,impact,source,published_at
```

Allowed labels:

```text
positive,neutral,negative
```

Raw datasets are not committed. Tests use a small committed fixture in `research/tests/fixtures`.

## Commands

```bash
uv run python -m economic_news_research.cli validate
uv run python -m economic_news_research.cli eda
uv run python -m economic_news_research.cli train-baseline
```

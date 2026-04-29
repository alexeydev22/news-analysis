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

Current package smoke check:

```bash
uv run python -c "from economic_news_research.paths import DEFAULT_RAW_DATASET; print(DEFAULT_RAW_DATASET)"
```

After the research CLI task is implemented, these commands will be available:

```bash
uv run python -m economic_news_research.cli validate
uv run python -m economic_news_research.cli eda
uv run python -m economic_news_research.cli train-baseline
uv run python -m economic_news_research.cli train-embedding
uv run python -m economic_news_research.cli train-transformer
uv run python -m economic_news_research.cli compare-models
```

Transformer and embedding model weights are downloaded into a local Hugging Face cache and
are not committed. Unit tests use fake model adapters and do not require network access.

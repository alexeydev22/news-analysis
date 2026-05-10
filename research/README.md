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

Training and comparison commands:

```bash
uv run python -m economic_news_research.cli validate
uv run python -m economic_news_research.cli eda
uv run python -m economic_news_research.cli train-baseline
uv run python -m economic_news_research.cli train-embedding
uv run python -m economic_news_research.cli train-transformer
just compare-models
just ml-report
just demo-up-trained
```

After training, `just compare-models` compares trained artifacts and
`just ml-report` writes `reports/ml/model-report.json` for the frontend ML report panel.
`just demo-up-trained` starts the demo with joblib classifiers enabled. The UI can switch
between trained `tfidf-logreg`, `embedding-logreg`, and `tiny-transformer-classifier`;
if an artifact is missing, the API returns a controlled unavailable-model error.

Transformer and embedding model weights are downloaded into a local Hugging Face cache and
are not committed. Unit tests use fake model adapters and do not require network access.

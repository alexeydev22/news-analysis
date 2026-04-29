from typing import Protocol

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV

from economic_news_research.data import DatasetSplit
from economic_news_research.metrics import compute_classification_metrics
from economic_news_research.model_selection import safe_cv
from economic_news_research.modeling import IMPACT_LABELS
from economic_news_research.results import ModelTrainingResult, measure_prediction_time

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


EmbeddingTrainingResult = ModelTrainingResult


class TextEmbedder(Protocol):
    def encode(self, texts: list[str]) -> np.ndarray: ...


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self.model_name = model_name
        self._model = None

    def encode(self, texts: list[str]) -> np.ndarray:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(embeddings)


def train_embedding_classifier(
    split: DatasetSplit,
    *,
    embedder: TextEmbedder | None = None,
    random_state: int,
) -> EmbeddingTrainingResult:
    active_embedder = embedder or SentenceTransformerEmbedder()
    train_embeddings = active_embedder.encode(split.train["text"].tolist())
    validation_embeddings = active_embedder.encode(split.validation["text"].tolist())
    test_texts = split.test["text"].tolist()

    search = GridSearchCV(
        estimator=LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=random_state,
        ),
        param_grid={"C": [0.1, 1.0, 10.0]},
        scoring="f1_macro",
        cv=safe_cv(split.train["impact"].tolist(), random_state=random_state),
        n_jobs=1,
    )
    search.fit(train_embeddings, split.train["impact"])

    best_estimator = search.best_estimator_
    validation_predictions = best_estimator.predict(validation_embeddings).tolist()
    test_predictions, inference_seconds_per_sample = measure_prediction_time(
        predictor=lambda values: best_estimator.predict(
            active_embedder.encode(list(values))
        ).tolist(),
        values=test_texts,
    )

    return EmbeddingTrainingResult(
        model_name="embedding-logreg",
        best_params=dict(search.best_params_),
        validation_metrics=compute_classification_metrics(
            y_true=split.validation["impact"].tolist(),
            y_pred=validation_predictions,
            labels=IMPACT_LABELS,
        ),
        test_metrics=compute_classification_metrics(
            y_true=split.test["impact"].tolist(),
            y_pred=test_predictions,
            labels=IMPACT_LABELS,
        ),
        estimator=best_estimator,
        inference_seconds_per_sample=inference_seconds_per_sample,
    )

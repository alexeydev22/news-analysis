from dataclasses import dataclass
from typing import Any, Protocol

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
        self._model: Any | None = None

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

    def __getstate__(self) -> dict[str, str]:
        return {"model_name": self.model_name}

    def __setstate__(self, state: dict[str, str]) -> None:
        self.model_name = state["model_name"]
        self._model = None


@dataclass
class EmbeddingTextClassifier:
    embedder: TextEmbedder
    classifier: LogisticRegression

    def predict(self, texts: list[str]) -> list[str]:
        embeddings = self.embedder.encode(texts)
        return self.classifier.predict(embeddings).tolist()


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

    classifier = search.best_estimator_
    estimator = EmbeddingTextClassifier(embedder=active_embedder, classifier=classifier)
    validation_predictions = classifier.predict(validation_embeddings).tolist()
    test_predictions, inference_seconds_per_sample = measure_prediction_time(
        predictor=lambda values: estimator.predict(list(values)),
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
        estimator=estimator,
        inference_seconds_per_sample=inference_seconds_per_sample,
    )

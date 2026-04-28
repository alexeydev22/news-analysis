from dataclasses import dataclass
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, LeaveOneOut, StratifiedKFold
from sklearn.pipeline import Pipeline

from economic_news_research.data import DatasetSplit
from economic_news_research.metrics import ClassificationMetrics, compute_classification_metrics

IMPACT_LABELS = ["negative", "neutral", "positive"]


@dataclass(frozen=True)
class BaselineTrainingResult:
    model_name: str
    best_params: dict[str, Any]
    validation_metrics: ClassificationMetrics
    test_metrics: ClassificationMetrics
    estimator: Pipeline


def build_baseline_pipeline(
    max_features: int,
    c_value: float,
    ngram_range: tuple[int, int],
) -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(max_features=max_features, ngram_range=ngram_range),
            ),
            (
                "classifier",
                LogisticRegression(
                    C=c_value,
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ],
    )


def train_baseline_model(
    split: DatasetSplit,
    *,
    random_state: int,
) -> BaselineTrainingResult:
    estimator = _build_training_pipeline(random_state=random_state)
    search = GridSearchCV(
        estimator=estimator,
        param_grid={
            "tfidf__max_features": [100, 1000],
            "tfidf__ngram_range": [(1, 1), (1, 2)],
            "classifier__C": [0.1, 1.0, 10.0],
        },
        scoring="f1_macro",
        cv=_safe_cv(split.train["impact"].tolist(), random_state=random_state),
        n_jobs=1,
    )
    search.fit(split.train["text"], split.train["impact"])

    best_estimator = search.best_estimator_
    validation_predictions = best_estimator.predict(split.validation["text"]).tolist()
    test_predictions = best_estimator.predict(split.test["text"]).tolist()

    return BaselineTrainingResult(
        model_name="tfidf-logreg",
        best_params=search.best_params_,
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
    )


def _build_training_pipeline(*, random_state: int) -> Pipeline:
    pipeline = build_baseline_pipeline(
        max_features=100,
        c_value=1.0,
        ngram_range=(1, 1),
    )
    classifier = pipeline.named_steps["classifier"]
    classifier.set_params(random_state=random_state)
    return pipeline


def _safe_cv(labels: list[str], *, random_state: int) -> LeaveOneOut | StratifiedKFold:
    class_counts = {label: labels.count(label) for label in set(labels)}
    min_class_count = min(class_counts.values())
    if min_class_count < 2:
        return LeaveOneOut()

    return StratifiedKFold(
        n_splits=min(3, min_class_count),
        shuffle=True,
        random_state=random_state,
    )

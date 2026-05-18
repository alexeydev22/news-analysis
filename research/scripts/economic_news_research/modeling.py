from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline

from economic_news_research.data import DatasetSplit
from economic_news_research.metrics import compute_classification_metrics
from economic_news_research.model_selection import safe_cv
from economic_news_research.results import ModelTrainingResult, measure_prediction_time

IMPACT_LABELS = ["negative", "neutral", "positive"]


BaselineTrainingResult = ModelTrainingResult


def build_baseline_pipeline(
    max_features: int,
    c_value: float,
    ngram_range: tuple[int, int],
    min_df: int = 2,
    max_df: float = 0.95,
    sublinear_tf: bool = True,
) -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    max_features=max_features,
                    ngram_range=ngram_range,
                    min_df=min_df,
                    max_df=max_df,
                    sublinear_tf=sublinear_tf,
                    strip_accents="unicode",
                    lowercase=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    C=c_value,
                    max_iter=1500,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ],
    )


def baseline_param_grid() -> dict[str, list[object]]:
    return {
        "tfidf__max_features": [20_000, 50_000],
        "tfidf__ngram_range": [(1, 2)],
        "tfidf__min_df": [2],
        "tfidf__max_df": [0.95],
        "tfidf__sublinear_tf": [True],
        "classifier__C": [1.0, 3.0],
    }


def train_baseline_model(
    split: DatasetSplit,
    *,
    random_state: int,
) -> BaselineTrainingResult:
    estimator = _build_training_pipeline(random_state=random_state)
    search = GridSearchCV(
        estimator=estimator,
        param_grid=baseline_param_grid(),
        scoring="f1_macro",
        cv=safe_cv(split.train["impact"].tolist(), random_state=random_state),
        n_jobs=1,
    )
    search.fit(split.train["text"], split.train["impact"])

    best_estimator = search.best_estimator_
    validation_predictions = best_estimator.predict(split.validation["text"]).tolist()
    test_predictions, inference_seconds_per_sample = measure_prediction_time(
        predictor=best_estimator.predict,
        values=split.test["text"].tolist(),
    )

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
        inference_seconds_per_sample=inference_seconds_per_sample,
    )


def _build_training_pipeline(*, random_state: int) -> Pipeline:
    pipeline = build_baseline_pipeline(
        max_features=20_000,
        c_value=1.0,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        sublinear_tf=True,
    )
    classifier = pipeline.named_steps["classifier"]
    classifier.set_params(random_state=random_state)
    return pipeline

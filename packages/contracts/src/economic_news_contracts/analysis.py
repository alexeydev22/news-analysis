from enum import StrEnum


class ImpactLabel(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class AnalysisModelName(StrEnum):
    TFIDF_LOGREG = "tfidf-logreg"
    RUBERT_TINY2_CLASSIFIER = "rubert-tiny2-classifier"
    RUBERT_TINY2_FINETUNED = "rubert-tiny2-finetuned"

from sklearn.model_selection import LeaveOneOut, StratifiedKFold


def safe_cv(labels: list[str], *, random_state: int) -> LeaveOneOut | StratifiedKFold:
    class_counts = {label: labels.count(label) for label in set(labels)}
    min_class_count = min(class_counts.values())
    if min_class_count < 2:
        return LeaveOneOut()

    return StratifiedKFold(
        n_splits=min(3, min_class_count),
        shuffle=True,
        random_state=random_state,
    )

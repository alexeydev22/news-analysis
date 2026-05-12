from collections import Counter, deque
from collections.abc import Mapping, Sequence

from economic_news_contracts.analysis import (
    ImpactLabel,
    TopicForecastItemResponse,
    TopicForecastNewsItemResponse,
)
from economic_news_contracts.dialog import DialogImpactSummary
from economic_news_contracts.retrieval import IndexedNewsDocument, NewsNeighborGroup


def build_topic_forecast(
    documents: Sequence[IndexedNewsDocument],
    neighbor_groups: Sequence[NewsNeighborGroup],
    impacts_by_news_id: Mapping[str, DialogImpactSummary],
    min_neighbor_score: float,
    max_topic_size: int,
) -> list[TopicForecastItemResponse]:
    """Строит тематический прогноз по документам, соседям и оценкам влияния.

    Args:
        documents: Проиндексированные новости для группировки.
        neighbor_groups: Найденные соседние новости по seed-документам.
        impacts_by_news_id: Оценки влияния по идентификатору новости.
        min_neighbor_score: Минимальный score для объединения в тему.
        max_topic_size: Максимальное количество новостей в одной теме.

    Returns:
        Список тем с агрегированным влиянием и кратким прогнозом.
    """
    if max_topic_size < 1:
        raise ValueError("max_topic_size must be positive")

    documents_by_id = {document.id: document for document in documents}
    document_order = {document.id: index for index, document in enumerate(documents)}
    graph, scores_by_news_id = _build_topic_graph(
        documents_by_id=documents_by_id,
        neighbor_groups=neighbor_groups,
        min_neighbor_score=min_neighbor_score,
    )

    topics: list[TopicForecastItemResponse] = []
    for component in _find_components(graph, document_order):
        for chunk in _split_component(component, max_topic_size):
            topic_documents = [documents_by_id[news_id] for news_id in chunk]
            topics.append(
                _build_topic_item(
                    topic_number=len(topics) + 1,
                    documents=topic_documents,
                    impacts_by_news_id=impacts_by_news_id,
                    scores_by_news_id=scores_by_news_id,
                )
            )
    return topics


def _build_topic_graph(
    documents_by_id: Mapping[str, IndexedNewsDocument],
    neighbor_groups: Sequence[NewsNeighborGroup],
    min_neighbor_score: float,
) -> tuple[dict[str, set[str]], dict[str, float]]:
    graph: dict[str, set[str]] = {news_id: set() for news_id in documents_by_id}
    scores_by_news_id: dict[str, float] = {}

    for group in neighbor_groups:
        if group.document_id not in documents_by_id:
            continue
        for neighbor in group.neighbors:
            if neighbor.id not in documents_by_id or neighbor.score < min_neighbor_score:
                continue
            graph[group.document_id].add(neighbor.id)
            graph[neighbor.id].add(group.document_id)
            scores_by_news_id[neighbor.id] = max(
                scores_by_news_id.get(neighbor.id, neighbor.score),
                neighbor.score,
            )

    return graph, scores_by_news_id


def _find_components(
    graph: Mapping[str, set[str]],
    document_order: Mapping[str, int],
) -> list[list[str]]:
    visited: set[str] = set()
    components: list[list[str]] = []

    for news_id in sorted(graph, key=document_order.__getitem__):
        if news_id in visited:
            continue
        component = _collect_component(news_id, graph, visited, document_order)
        components.append(component)

    return components


def _collect_component(
    start_news_id: str,
    graph: Mapping[str, set[str]],
    visited: set[str],
    document_order: Mapping[str, int],
) -> list[str]:
    queue: deque[str] = deque([start_news_id])
    visited.add(start_news_id)
    component: list[str] = []

    while queue:
        news_id = queue.popleft()
        component.append(news_id)
        for neighbor_id in sorted(graph[news_id], key=document_order.__getitem__):
            if neighbor_id in visited:
                continue
            visited.add(neighbor_id)
            queue.append(neighbor_id)

    return sorted(component, key=document_order.__getitem__)


def _split_component(
    component: Sequence[str],
    max_topic_size: int,
) -> list[list[str]]:
    return [
        list(component[index : index + max_topic_size])
        for index in range(0, len(component), max_topic_size)
    ]


def _build_topic_item(
    topic_number: int,
    documents: Sequence[IndexedNewsDocument],
    impacts_by_news_id: Mapping[str, DialogImpactSummary],
    scores_by_news_id: Mapping[str, float],
) -> TopicForecastItemResponse:
    impact_counts = _count_impacts(documents, impacts_by_news_id)
    overall_impact = _choose_overall_impact(impact_counts)
    confidence = _calculate_confidence(documents, impacts_by_news_id)

    return TopicForecastItemResponse(
        topic_id=f"topic-{topic_number}",
        title=documents[0].title,
        summary=_build_summary(documents),
        overall_impact=overall_impact,
        confidence=confidence,
        positive_count=impact_counts[ImpactLabel.POSITIVE],
        neutral_count=impact_counts[ImpactLabel.NEUTRAL],
        negative_count=impact_counts[ImpactLabel.NEGATIVE],
        forecast=_build_forecast(overall_impact),
        arguments=_build_arguments(impact_counts),
        risks=_build_risks(overall_impact),
        news=[
            _build_news_item(document, impacts_by_news_id, scores_by_news_id)
            for document in documents
        ],
    )


def _count_impacts(
    documents: Sequence[IndexedNewsDocument],
    impacts_by_news_id: Mapping[str, DialogImpactSummary],
) -> Counter[ImpactLabel]:
    impact_counts: Counter[ImpactLabel] = Counter()
    for document in documents:
        summary = impacts_by_news_id.get(document.id)
        if summary is not None:
            impact_counts[summary.impact] += 1
    return impact_counts


def _choose_overall_impact(
    impact_counts: Counter[ImpactLabel],
) -> ImpactLabel:
    if not impact_counts:
        return ImpactLabel.NEUTRAL

    top_count = max(impact_counts.values(), default=0)
    leaders = [impact for impact, count in impact_counts.items() if count == top_count]
    if len(leaders) != 1:
        return ImpactLabel.NEUTRAL
    return leaders[0]


def _calculate_confidence(
    documents: Sequence[IndexedNewsDocument],
    impacts_by_news_id: Mapping[str, DialogImpactSummary],
) -> float:
    confidence_values = [
        summary.confidence
        for document in documents
        if (summary := impacts_by_news_id.get(document.id)) is not None
        and summary.confidence is not None
    ]
    if not confidence_values:
        return 0.0
    return sum(confidence_values) / len(confidence_values)


def _build_summary(documents: Sequence[IndexedNewsDocument]) -> str:
    if len(documents) == 1:
        return documents[0].title
    titles = "; ".join(document.title for document in documents[:3])
    return f"Тема объединяет {len(documents)} новости: {titles}."


def _build_forecast(overall_impact: ImpactLabel) -> str:
    if overall_impact == ImpactLabel.POSITIVE:
        direction = "преобладает положительный сигнал"
    elif overall_impact == ImpactLabel.NEGATIVE:
        direction = "преобладает отрицательный сигнал"
    else:
        direction = "сигналы неоднозначны или сбалансированы"

    return (
        f"По совокупности новостей {direction}; вывод следует использовать "
        "как аналитическую оценку сценария, это не финансовая рекомендация."
    )


def _build_arguments(impact_counts: Counter[ImpactLabel]) -> list[str]:
    return [
        "Оценка построена по большинству impact-меток внутри темы.",
        (
            "Распределение сигналов: "
            f"positive={impact_counts[ImpactLabel.POSITIVE]}, "
            f"neutral={impact_counts[ImpactLabel.NEUTRAL]}, "
            f"negative={impact_counts[ImpactLabel.NEGATIVE]}."
        ),
    ]


def _build_risks(overall_impact: ImpactLabel) -> list[str]:
    if overall_impact == ImpactLabel.NEUTRAL:
        return ["Баланс или отсутствие сигналов повышает неопределенность прогноза."]
    return ["Прогноз зависит от полноты набора новостей и качества impact-оценок."]


def _build_news_item(
    document: IndexedNewsDocument,
    impacts_by_news_id: Mapping[str, DialogImpactSummary],
    scores_by_news_id: Mapping[str, float],
) -> TopicForecastNewsItemResponse:
    summary = impacts_by_news_id.get(document.id)
    impact = summary.impact if summary else ImpactLabel.NEUTRAL
    return TopicForecastNewsItemResponse(
        id=document.id,
        title=document.title,
        text=document.text,
        source=document.source,
        impact=impact,
        score=scores_by_news_id.get(document.id),
    )

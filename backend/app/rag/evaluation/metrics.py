"""Deterministic metrics for a labelled Secure RAG evaluation dataset."""

from dataclasses import asdict, dataclass
from statistics import fmean


@dataclass(frozen=True, slots=True)
class EvaluationObservation:
    """Expected evidence and one observed retrieval/query result."""

    case_id: str
    expected_document_ids: frozenset[str]
    returned_document_ids: tuple[str, ...] = ()
    retrieved_chunk_ids: frozenset[str] = frozenset()
    cited_chunk_ids: tuple[str, ...] = ()
    expected_empty: bool = False
    expected_denied: bool = False
    status_code: int = 200


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Aggregate research metrics in the zero-to-one range."""

    case_count: int
    precision_at_k: float
    recall_at_k: float
    mean_reciprocal_rank: float
    empty_result_accuracy: float
    authorization_accuracy: float
    citation_integrity: float

    def to_dict(self) -> dict[str, int | float]:
        """Return a JSON-serializable representation."""

        return asdict(self)


def _mean(values: list[float]) -> float:
    return fmean(values) if values else 1.0


def precision(observation: EvaluationObservation) -> float:
    """Measure the fraction of returned chunks belonging to relevant documents."""

    if not observation.returned_document_ids:
        return 1.0 if observation.expected_empty else 0.0
    relevant = sum(
        document_id in observation.expected_document_ids
        for document_id in observation.returned_document_ids
    )
    return relevant / len(observation.returned_document_ids)


def recall(observation: EvaluationObservation) -> float:
    """Measure the fraction of expected documents represented in the results."""

    if not observation.expected_document_ids:
        return 1.0 if not observation.returned_document_ids else 0.0
    returned = set(observation.returned_document_ids)
    return len(returned & observation.expected_document_ids) / len(
        observation.expected_document_ids
    )


def reciprocal_rank(observation: EvaluationObservation) -> float:
    """Score how early the first relevant chunk appears."""

    for index, document_id in enumerate(observation.returned_document_ids, start=1):
        if document_id in observation.expected_document_ids:
            return 1.0 / index
    return 1.0 if observation.expected_empty and not observation.returned_document_ids else 0.0


def citation_integrity(observation: EvaluationObservation) -> float:
    """Ensure every citation references a chunk actually supplied to generation."""

    if not observation.cited_chunk_ids:
        return 1.0
    valid = sum(
        chunk_id in observation.retrieved_chunk_ids
        for chunk_id in observation.cited_chunk_ids
    )
    return valid / len(observation.cited_chunk_ids)


def evaluate(observations: list[EvaluationObservation]) -> EvaluationReport:
    """Calculate retrieval, denial, empty-result, and citation metrics."""

    retrieval_cases = [case for case in observations if not case.expected_denied]
    empty_cases = [case for case in observations if case.expected_empty]
    denied_cases = [case for case in observations if case.expected_denied]
    citation_cases = [case for case in observations if case.cited_chunk_ids]
    return EvaluationReport(
        case_count=len(observations),
        precision_at_k=_mean([precision(case) for case in retrieval_cases]),
        recall_at_k=_mean([recall(case) for case in retrieval_cases]),
        mean_reciprocal_rank=_mean(
            [reciprocal_rank(case) for case in retrieval_cases]
        ),
        empty_result_accuracy=_mean(
            [
                float(case.status_code == 200 and not case.returned_document_ids)
                for case in empty_cases
            ]
        ),
        authorization_accuracy=_mean(
            [float(case.status_code in {403, 404}) for case in denied_cases]
        ),
        citation_integrity=_mean(
            [citation_integrity(case) for case in citation_cases]
        ),
    )

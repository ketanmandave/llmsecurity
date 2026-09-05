"""Tests for hybrid score fusion and dynamic relevance pruning."""

import unittest
import uuid

from app.config import Settings
from app.retrieval.ranking import rank_candidates
from app.retrieval.retriever import RetrievedChunk, _tsquery_text


def candidate(
    name: str,
    vector: float,
    lexical: float,
    title: float,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_name=name,
        page_number=1,
        content="candidate text",
        score=vector,
        vector_score=vector,
        lexical_score=lexical,
        title_score=title,
    )


class FakeReranker:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores

    async def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[float]:
        return self.scores


class HybridRankingTests(unittest.IsolatedAsyncioTestCase):
    def test_query_terms_remove_stop_words_and_are_safe(self) -> None:
        self.assertEqual(
            _tsquery_text("Which topics are given for ISE of cybersecurity?"),
            "topics | ise | cybersecurity",
        )

    async def test_relative_cutoff_removes_unrelated_resume(self) -> None:
        notice_page_1 = candidate("ISE 1 Notice", 0.7377, 0.8, 1.0)
        notice_page_2 = candidate("ISE 1 Notice", 0.7150, 1.0, 1.0)
        resume = candidate("Ketan Resume", 0.5199, 0.1, 0.0)

        results = await rank_candidates(
            question="Which topics are given for ISE of cybersecurity?",
            candidates=[notice_page_1, notice_page_2, resume],
            top_k=5,
            settings=Settings(),
            reranker=FakeReranker([5.0, 5.0, -1.0]),
        )

        self.assertEqual(len(results), 2)
        self.assertEqual({item.document_name for item in results}, {"ISE 1 Notice"})
        self.assertTrue(all(item.reranker_score is not None for item in results))

    async def test_top_k_is_applied_after_ranking(self) -> None:
        results = await rank_candidates(
            question="leave policy",
            candidates=[
                candidate("A", 0.9, 1.0, 1.0),
                candidate("B", 0.89, 0.9, 0.9),
            ],
            top_k=1,
            settings=Settings(),
            reranker=FakeReranker([4.0, 3.0]),
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].document_name, "A")


if __name__ == "__main__":
    unittest.main()

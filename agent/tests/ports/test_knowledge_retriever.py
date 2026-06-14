import asyncio

import pytest

from analyze_agent.domain.models import KnowledgeChunk
from analyze_agent.ports.knowledge_retriever import KnowledgeBaseRetriever
from analyze_agent.ports.retriever_errors import (
    InvalidKnowledgeResponse,
    KnowledgeRetrievalError,
    KnowledgeRetrievalTimeout,
)


class ExampleRetriever:
    async def search(self, text: str) -> list[KnowledgeChunk]:
        return [KnowledgeChunk(chunk_id="chunk-1", text=text)]


def test_protocol_accepts_structural_async_implementation() -> None:
    retriever = ExampleRetriever()

    assert isinstance(retriever, KnowledgeBaseRetriever)
    chunks = asyncio.run(retriever.search("ADC Basel requirement"))
    assert chunks == [
        KnowledgeChunk(chunk_id="chunk-1", text="ADC Basel requirement")
    ]


@pytest.mark.parametrize(
    ("error", "retryable"),
    [
        (KnowledgeRetrievalTimeout(), True),
        (InvalidKnowledgeResponse(), False),
    ],
)
def test_retrieval_errors_expose_retryability(
    error: KnowledgeRetrievalError,
    retryable: bool,
) -> None:
    assert error.retryable is retryable


def test_normalized_chunk_rejects_invalid_similarity() -> None:
    with pytest.raises(ValueError):
        KnowledgeChunk(text="content", similarity_score=1.1)

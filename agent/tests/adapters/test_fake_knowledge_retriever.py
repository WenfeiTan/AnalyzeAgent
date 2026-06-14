import asyncio
from pathlib import Path

import pytest

from analyze_agent.adapters.fake_knowledge_retriever import (
    FakeKnowledgeBaseRetriever,
    load_fake_scenario,
)
from analyze_agent.ports.retriever_errors import (
    InvalidKnowledgeResponse,
    KnowledgeRetrievalTimeout,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "vector_mcp"


@pytest.mark.parametrize(
    ("fixture_name", "expected_count"),
    [
        ("empty.json", 0),
        ("complete_mapping.json", 1),
        ("partial_mapping.json", 1),
        ("no_evidence.json", 1),
    ],
)
def test_fake_retriever_returns_fixture_chunks(
    fixture_name: str,
    expected_count: int,
) -> None:
    scenario = load_fake_scenario(FIXTURES / fixture_name)
    retriever = FakeKnowledgeBaseRetriever({"query": scenario})

    chunks = asyncio.run(retriever.search("query"))

    assert len(chunks) == expected_count
    assert retriever.queries == ["query"]


def test_unknown_query_defaults_to_empty_knowledge_base() -> None:
    retriever = FakeKnowledgeBaseRetriever()

    assert asyncio.run(retriever.search("unknown requirement")) == []


def test_timeout_fixture_raises_typed_timeout() -> None:
    scenario = load_fake_scenario(FIXTURES / "timeout.json")
    retriever = FakeKnowledgeBaseRetriever({"query": scenario})

    with pytest.raises(KnowledgeRetrievalTimeout):
        asyncio.run(retriever.search("query"))


def test_invalid_fixture_is_rejected_during_loading() -> None:
    with pytest.raises(InvalidKnowledgeResponse):
        load_fake_scenario(FIXTURES / "invalid.json")


def test_results_are_copied_for_each_call() -> None:
    scenario = load_fake_scenario(FIXTURES / "complete_mapping.json")
    retriever = FakeKnowledgeBaseRetriever({"query": scenario})

    first = asyncio.run(retriever.search("query"))
    second = asyncio.run(retriever.search("query"))
    first.clear()

    assert len(second) == 1


import asyncio

import pytest

from analyze_agent.adapters.resilient import (
    ResilientKnowledgeBaseRetriever,
    ResilientRequirementAnalyzer,
)
from analyze_agent.domain.models import (
    AnalyzedRequirement,
    KnowledgeChunk,
    RequirementAnalysisSignals,
)
from analyze_agent.ports.analyzer_errors import RequirementAnalysisError
from analyze_agent.ports.retriever_errors import KnowledgeRetrievalTimeout
from analyze_agent.resilience import RetryPolicy


class FlakyRetriever:
    def __init__(self) -> None:
        self.calls = 0

    async def search(self, text: str) -> list[KnowledgeChunk]:
        self.calls += 1
        if self.calls == 1:
            raise KnowledgeRetrievalTimeout()
        return [KnowledgeChunk(text=text)]


class SlowRetriever:
    async def search(self, text: str) -> list[KnowledgeChunk]:
        await asyncio.sleep(0.05)
        return [KnowledgeChunk(text=text)]


class FlakyAnalyzer:
    def __init__(self) -> None:
        self.calls = 0

    async def analyze(self, requirement: str) -> RequirementAnalysisSignals:
        self.calls += 1
        if self.calls == 1:
            raise RequirementAnalysisError("temporary", retryable=True)
        return RequirementAnalysisSignals(
            analyzed_requirement=AnalyzedRequirement(
                summary=requirement,
                business_goal="Test resilience.",
            )
        )


def test_retriever_retries_retryable_failure() -> None:
    delegate = FlakyRetriever()
    retriever = ResilientKnowledgeBaseRetriever(
        delegate,
        RetryPolicy(timeout_seconds=1, max_attempts=2, base_delay_seconds=0),
    )

    chunks = asyncio.run(retriever.search("ADC"))

    assert len(chunks) == 1
    assert delegate.calls == 2


def test_retriever_maps_timeout_after_bounded_attempts() -> None:
    retriever = ResilientKnowledgeBaseRetriever(
        SlowRetriever(),
        RetryPolicy(
            timeout_seconds=0.001,
            max_attempts=1,
            base_delay_seconds=0,
        ),
    )

    with pytest.raises(KnowledgeRetrievalTimeout):
        asyncio.run(retriever.search("ADC"))


def test_analyzer_retries_retryable_model_failure() -> None:
    delegate = FlakyAnalyzer()
    analyzer = ResilientRequirementAnalyzer(
        delegate,
        RetryPolicy(timeout_seconds=1, max_attempts=2, base_delay_seconds=0),
    )

    result = asyncio.run(analyzer.analyze("Build an ADC GDA."))

    assert result.analyzed_requirement.business_goal == "Test resilience."
    assert delegate.calls == 2

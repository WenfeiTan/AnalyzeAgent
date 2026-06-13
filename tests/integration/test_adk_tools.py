import asyncio

import pytest

from analyze_agent.adapters.fake_knowledge_retriever import (
    FakeKnowledgeBaseRetriever,
    FakeRetrievalScenario,
)
from analyze_agent.agent import root_agent
from analyze_agent.config import Settings
from analyze_agent.domain.models import (
    AnalyzedRequirement,
    KeywordAnalysisSignal,
    KeywordStrength,
    KnowledgeChunk,
    RequirementAnalysisSignals,
    RequirementUpdateSignals,
)
from analyze_agent.persistence.sqlite_repository import SQLiteRequirementRepository
from analyze_agent.runtime import build_runtime, configure_runtime
from analyze_agent.tools import (
    analyze_initial,
    analyze_update,
    search_knowledge_base,
)


class StubAnalyzer:
    async def analyze(self, requirement: str) -> RequirementAnalysisSignals:
        return RequirementAnalysisSignals(
            analyzed_requirement=AnalyzedRequirement(
                summary=requirement,
                business_goal="Support ADC review.",
            ),
            keywords=[
                KeywordAnalysisSignal(
                    name="ADC",
                    strength=KeywordStrength.CORE,
                    rationale="Core domain.",
                )
            ],
        )


class StubUpdater:
    async def update(self, **kwargs) -> RequirementUpdateSignals:
        return RequirementUpdateSignals(
            full_requirement="Build an updated ADC review GDA."
        )


class StubReconstructor:
    async def reconstruct(self, **kwargs):
        from analyze_agent.domain.models import KnowledgeReuseSignals

        return KnowledgeReuseSignals()


@pytest.fixture(autouse=True)
def reset_runtime() -> None:
    configure_runtime(None)
    yield
    configure_runtime(None)


@pytest.fixture
def injected_runtime(tmp_path):
    repository = SQLiteRequirementRepository(tmp_path / "adk.sqlite3")
    repository.initialize()
    retriever = FakeKnowledgeBaseRetriever(
        default_scenario=FakeRetrievalScenario(
            chunks=(KnowledgeChunk(chunk_id="chunk-1", text="ADC context"),)
        )
    )
    runtime = build_runtime(
        Settings(
            google_api_key=None,
            model="gemini-test",
            log_level="INFO",
            database_path=tmp_path / "unused.sqlite3",
        ),
        analyzer=StubAnalyzer(),
        updater=StubUpdater(),
        reconstructor=StubReconstructor(),
        retriever=retriever,
        repository=repository,
    )
    configure_runtime(runtime)
    return runtime


def test_root_agent_registers_stable_tools() -> None:
    tool_names = {tool.__name__ for tool in root_agent.tools}

    assert tool_names == {
        "analyze_initial",
        "analyze_update",
        "search_knowledge_base",
    }


def test_adk_tools_run_initial_update_and_search(injected_runtime) -> None:
    initial = asyncio.run(analyze_initial("Build an ADC review GDA."))
    updated = asyncio.run(
        analyze_update(
            initial["requirement_id"],
            supplemental_information="Update the ADC review scope.",
        )
    )
    search = asyncio.run(search_knowledge_base("ADC"))

    assert initial["keywords"][0]["name"] == "ADC"
    assert updated["requirement_id"] == initial["requirement_id"]
    assert updated["revision_id"] != initial["revision_id"]
    assert search["chunks"][0]["chunk_id"] == "chunk-1"

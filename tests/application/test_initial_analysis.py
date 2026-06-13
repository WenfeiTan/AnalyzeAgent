import asyncio

import pytest

from analyze_agent.adapters.fake_knowledge_retriever import (
    FakeKnowledgeBaseRetriever,
    FakeRetrievalScenario,
)
from analyze_agent.application.errors import UnsupportedRequirementLanguage
from analyze_agent.application.initial_analysis import InitialAnalysisService
from analyze_agent.domain.models import (
    AnalyzedRequirement,
    FieldAnalysisSignal,
    InitialAnalysisRequest,
    KeywordAnalysisSignal,
    KeywordStrength,
    RequirementAnalysisSignals,
)
from analyze_agent.persistence.sqlite_repository import SQLiteRequirementRepository
from analyze_agent.ports.retriever_errors import KnowledgeRetrievalTimeout


class StubAnalyzer:
    async def analyze(self, requirement: str) -> RequirementAnalysisSignals:
        return RequirementAnalysisSignals(
            analyzed_requirement=AnalyzedRequirement(
                summary="Build a Basel 3 ADC review GDA.",
                business_goal="Support the updated ADC review.",
                domain_context=["ADC", "Basel 3"],
            ),
            clear_fields=[
                FieldAnalysisSignal(
                    name="Facility_id",
                    requirement_excerpt="needs Facility_id",
                )
            ],
            keywords=[
                KeywordAnalysisSignal(
                    name="ADC",
                    strength=KeywordStrength.CORE,
                    rationale="Core review domain.",
                ),
                KeywordAnalysisSignal(
                    name="Basel 3",
                    strength=KeywordStrength.CORE,
                    rationale="Regulatory context.",
                ),
            ],
        )


@pytest.fixture
def repository(tmp_path) -> SQLiteRequirementRepository:
    result = SQLiteRequirementRepository(tmp_path / "initial.sqlite3")
    result.initialize()
    return result


def _service(
    repository: SQLiteRequirementRepository,
    retriever: FakeKnowledgeBaseRetriever | None = None,
) -> InitialAnalysisService:
    return InitialAnalysisService(
        analyzer=StubAnalyzer(),
        retriever=retriever or FakeKnowledgeBaseRetriever(),
        repository=repository,
        model="gemini-test",
        prompt_version="analyze-requirement-v1",
    )


def test_initial_analysis_builds_and_persists_grouped_output(
    repository: SQLiteRequirementRepository,
) -> None:
    request = InitialAnalysisRequest(
        requirement=(
            "Build a Basel 3 ADC review GDA that needs Facility_id."
        )
    )

    response = asyncio.run(_service(repository).analyze_initial(request))
    revision = repository.get_latest_revision(response.requirement_id)

    assert response.request_id == request.request_id
    assert response.clear_fields[0].name == "Facility_id"
    assert response.clear_fields[0].confidence.score == 0.7
    assert [item.name for item in response.keywords] == ["ADC", "Basel 3"]
    assert [item.priority for item in response.keywords] == [2, 3]
    assert response.reused_mappings == []
    assert revision.revision_id == response.revision_id
    assert revision.output_snapshot == response.model_dump(mode="json")


def test_initial_analysis_degrades_when_retrieval_times_out(
    repository: SQLiteRequirementRepository,
) -> None:
    retriever = FakeKnowledgeBaseRetriever(
        default_scenario=FakeRetrievalScenario(
            error=KnowledgeRetrievalTimeout()
        )
    )

    response = asyncio.run(
        _service(repository, retriever)
        .analyze_initial(
            InitialAnalysisRequest(requirement="Build an ADC review GDA.")
        )
    )

    assert response.clear_fields
    assert response.warnings == ["Knowledge Base retrieval timed out."]


def test_initial_analysis_rejects_non_english_requirement(
    repository: SQLiteRequirementRepository,
) -> None:
    with pytest.raises(UnsupportedRequirementLanguage):
        asyncio.run(
            _service(repository)
            .analyze_initial(InitialAnalysisRequest(requirement="构建一个GDA"))
        )


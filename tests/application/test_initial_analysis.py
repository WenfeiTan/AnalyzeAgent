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
    AssetReference,
    AttributeReference,
    FieldAnalysisSignal,
    InitialAnalysisRequest,
    KeywordAnalysisSignal,
    KeywordStrength,
    KnowledgeChunk,
    KnowledgeMappingCandidate,
    KnowledgeReuseSignals,
    RequirementAnalysisSignals,
    SourceAttributeMapping,
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


class StubReconstructor:
    async def reconstruct(self, **kwargs) -> KnowledgeReuseSignals:
        return KnowledgeReuseSignals(
            candidates=[
                KnowledgeMappingCandidate(
                    field_name="ADC_entity_country",
                    sources=[
                        SourceAttributeMapping(
                            attribute=AttributeReference(
                                attribute_name="entity_country"
                            ),
                            asset=AssetReference(asset_name="adc_entity"),
                        )
                    ],
                    supporting_chunk_ids=["success-case-001"],
                    success_case_confirmed=True,
                    intent_match=True,
                    domain_compatible=True,
                    business_definition_compatible=True,
                    rationale="Previously successful mapping.",
                )
            ]
        )


@pytest.fixture
def repository(tmp_path) -> SQLiteRequirementRepository:
    result = SQLiteRequirementRepository(tmp_path / "initial.sqlite3")
    result.initialize()
    return result


def _service(
    repository: SQLiteRequirementRepository,
    retriever: FakeKnowledgeBaseRetriever | None = None,
    reconstructor=None,
) -> InitialAnalysisService:
    return InitialAnalysisService(
        analyzer=StubAnalyzer(),
        retriever=retriever or FakeKnowledgeBaseRetriever(),
        repository=repository,
        model="gemini-test",
        prompt_version="analyze-requirement-v1",
        knowledge_reconstructor=reconstructor,
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


def test_initial_analysis_includes_verified_reused_mapping(
    repository: SQLiteRequirementRepository,
) -> None:
    retriever = FakeKnowledgeBaseRetriever(
        default_scenario=FakeRetrievalScenario(
            chunks=(
                KnowledgeChunk(
                    chunk_id="success-case-001",
                    text=(
                        "Successful ADC_entity_country mapping uses "
                        "entity_country on adc_entity."
                    ),
                    metadata={"case_status": "success"},
                ),
            )
        )
    )

    response = asyncio.run(
        _service(repository, retriever, StubReconstructor())
        .analyze_initial(
            InitialAnalysisRequest(requirement="Build an ADC review GDA.")
        )
    )

    assert response.reused_mappings[0].field_name == "ADC_entity_country"
    assert response.reused_mappings[0].priority == 1
    assert response.clear_fields[0].priority == 2


def test_initial_analysis_rejects_non_english_requirement(
    repository: SQLiteRequirementRepository,
) -> None:
    with pytest.raises(UnsupportedRequirementLanguage):
        asyncio.run(
            _service(repository)
            .analyze_initial(InitialAnalysisRequest(requirement="构建一个GDA"))
        )

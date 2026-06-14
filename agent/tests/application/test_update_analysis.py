import asyncio

import pytest

from analyze_agent.adapters.fake_knowledge_retriever import (
    FakeKnowledgeBaseRetriever,
)
from analyze_agent.application.analysis_pipeline import AnalysisPipeline
from analyze_agent.application.errors import UnsupportedRequirementLanguage
from analyze_agent.application.initial_analysis import InitialAnalysisService
from analyze_agent.application.update_analysis import UpdatedAnalysisService
from analyze_agent.domain.models import (
    AnalyzedRequirement,
    AssetReference,
    AttributeReference,
    ChangeAction,
    FeedbackDecision,
    FeedbackTargetType,
    FieldAnalysisSignal,
    InitialAnalysisRequest,
    KeywordAnalysisSignal,
    KeywordStrength,
    RequirementAnalysisSignals,
    RequirementChange,
    RequirementUpdateSignals,
    SearchFeedback,
    UpdatedAnalysisRequest,
)
from analyze_agent.persistence.sqlite_repository import SQLiteRequirementRepository
from analyze_agent.workflow_events import (
    MemoryStageEventSink,
    StageStatus,
    WorkflowStage,
)


class StubAnalyzer:
    async def analyze(self, requirement: str) -> RequirementAnalysisSignals:
        return RequirementAnalysisSignals(
            analyzed_requirement=AnalyzedRequirement(
                summary=requirement,
                business_goal="Support ADC review.",
                domain_context=["ADC"],
            ),
            clear_fields=[
                FieldAnalysisSignal(
                    name="Facility_id",
                    requirement_excerpt="Facility_id",
                )
            ],
            keywords=[
                KeywordAnalysisSignal(
                    name="ADC",
                    strength=KeywordStrength.CORE,
                    rationale="Core review domain.",
                )
            ],
        )


class StubUpdater:
    async def update(self, **kwargs) -> RequirementUpdateSignals:
        return RequirementUpdateSignals(
            full_requirement=(
                "Build an ADC review GDA including ADC_entity_country."
            ),
            changes=[
                RequirementChange(
                    action=ChangeAction.ADD,
                    target="ADC_entity_country",
                    after="Include ADC entity country.",
                )
            ],
        )


@pytest.fixture
def repository(tmp_path) -> SQLiteRequirementRepository:
    result = SQLiteRequirementRepository(tmp_path / "updates.sqlite3")
    result.initialize()
    return result


def _pipeline() -> AnalysisPipeline:
    return AnalysisPipeline(
        analyzer=StubAnalyzer(),
        retriever=FakeKnowledgeBaseRetriever(),
        model="gemini-test",
        prompt_version="analyze-requirement-v1",
    )


def _create_initial(repository: SQLiteRequirementRepository):
    service = InitialAnalysisService(
        analyzer=StubAnalyzer(),
        retriever=FakeKnowledgeBaseRetriever(),
        repository=repository,
        model="gemini-test",
        prompt_version="analyze-requirement-v1",
    )
    return asyncio.run(
        service.analyze_initial(
            InitialAnalysisRequest(requirement="Build an ADC review GDA.")
        )
    )


def test_update_creates_complete_second_revision(
    repository: SQLiteRequirementRepository,
) -> None:
    initial = _create_initial(repository)
    sink = MemoryStageEventSink()
    service = UpdatedAnalysisService(
        updater=StubUpdater(),
        pipeline=_pipeline(),
        repository=repository,
    )

    response = asyncio.run(
        service.analyze_update(
            UpdatedAnalysisRequest(
                requirement_id=initial.requirement_id,
                supplemental_information="Include ADC entity country.",
            ),
            event_sink=sink,
            job_id="update-job",
        )
    )
    history = repository.list_revisions(initial.requirement_id)

    assert len(history) == 2
    assert history[1].full_requirement == (
        "Build an ADC review GDA including ADC_entity_country."
    )
    assert history[1].supplemental_information == (
        "Include ADC entity country."
    )
    assert response.change_summary is not None
    assert [
        event.stage
        for event in sink.events
        if event.status is StageStatus.COMPLETED
    ] == [
        WorkflowStage.VALIDATING_INPUT,
        WorkflowStage.LOADING_REVISION,
        WorkflowStage.UPDATING_REQUIREMENT,
        WorkflowStage.ANALYZING_REQUIREMENT,
        WorkflowStage.SEARCHING_KNOWLEDGE_BASE,
        WorkflowStage.RECONSTRUCTING_MAPPINGS,
        WorkflowStage.CALCULATING_CONFIDENCE,
        WorkflowStage.PERSISTING_REVISION,
        WorkflowStage.COMPLETED,
    ]
    assert response.change_summary.changes[0].action is ChangeAction.ADD
    assert history[1].output_snapshot == response.model_dump(mode="json")


def test_reject_feedback_is_enforced_after_reanalysis(
    repository: SQLiteRequirementRepository,
) -> None:
    initial = _create_initial(repository)
    feedback = SearchFeedback(
        candidate_id="candidate-1",
        target_type=FeedbackTargetType.FIELD_MAPPING,
        decision=FeedbackDecision.REJECT,
        field_name="Facility_id",
        asset=AssetReference(asset_name="facility"),
        attribute=AttributeReference(attribute_name="facility_id"),
        reason="This field is not needed.",
    )
    service = UpdatedAnalysisService(
        updater=StubUpdater(),
        pipeline=_pipeline(),
        repository=repository,
    )

    response = asyncio.run(
        service.analyze_update(
            UpdatedAnalysisRequest(
                requirement_id=initial.requirement_id,
                search_feedback=[feedback],
            )
        )
    )

    assert response.clear_fields == []
    assert "Facility_id" in response.analyzed_requirement.negative_constraints
    assert response.change_summary is not None
    assert response.change_summary.changes[-1].action is ChangeAction.REJECT


def test_accept_mapping_creates_user_feedback_evidence(
    repository: SQLiteRequirementRepository,
) -> None:
    initial = _create_initial(repository)
    feedback = SearchFeedback(
        candidate_id="candidate-2",
        target_type=FeedbackTargetType.FIELD_MAPPING,
        decision=FeedbackDecision.ACCEPT,
        field_name="ADC_entity_country",
        asset=AssetReference(asset_name="adc_entity"),
        attribute=AttributeReference(attribute_name="entity_country"),
        reason="Confirmed from the search result.",
    )
    service = UpdatedAnalysisService(
        updater=StubUpdater(),
        pipeline=_pipeline(),
        repository=repository,
    )

    response = asyncio.run(
        service.analyze_update(
            UpdatedAnalysisRequest(
                requirement_id=initial.requirement_id,
                search_feedback=[feedback],
            )
        )
    )
    revision = repository.get_latest_revision(initial.requirement_id)

    assert response.reused_mappings[0].confidence.score == 0.8
    assert response.reused_mappings[0].evidence[0].reference == "candidate-2"
    assert revision.feedback == [feedback]


def test_non_english_supplement_is_rejected_before_update(
    repository: SQLiteRequirementRepository,
) -> None:
    initial = _create_initial(repository)
    service = UpdatedAnalysisService(
        updater=StubUpdater(),
        pipeline=_pipeline(),
        repository=repository,
    )

    with pytest.raises(UnsupportedRequirementLanguage):
        asyncio.run(
            service.analyze_update(
                UpdatedAnalysisRequest(
                    requirement_id=initial.requirement_id,
                    supplemental_information="增加国家字段",
                )
            )
        )

    assert len(repository.list_revisions(initial.requirement_id)) == 1

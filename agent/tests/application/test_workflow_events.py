import asyncio

import pytest

from analyze_agent.adapters.fake_knowledge_retriever import (
    FakeKnowledgeBaseRetriever,
)
from analyze_agent.application.initial_analysis import InitialAnalysisService
from analyze_agent.domain.models import (
    AnalyzedRequirement,
    InitialAnalysisRequest,
    RequirementAnalysisSignals,
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
                business_goal="Test workflow events.",
            )
        )


class FailingAnalyzer:
    async def analyze(self, requirement: str) -> RequirementAnalysisSignals:
        raise RuntimeError(f"analysis failed for {len(requirement)} characters")


@pytest.fixture
def repository(tmp_path) -> SQLiteRequirementRepository:
    result = SQLiteRequirementRepository(tmp_path / "events.sqlite3")
    result.initialize()
    return result


def _service(
    repository: SQLiteRequirementRepository,
    analyzer=None,
) -> InitialAnalysisService:
    return InitialAnalysisService(
        analyzer=analyzer or StubAnalyzer(),
        retriever=FakeKnowledgeBaseRetriever(),
        repository=repository,
        model="gemini-test",
        prompt_version="test-v1",
    )


def test_initial_workflow_emits_ordered_real_stage_events(
    repository: SQLiteRequirementRepository,
) -> None:
    sink = MemoryStageEventSink()
    request = InitialAnalysisRequest(requirement="Build an ADC review GDA.")

    asyncio.run(
        _service(repository).analyze_initial(
            request,
            event_sink=sink,
            job_id="job-123",
        )
    )

    assert [event.sequence for event in sink.events] == list(
        range(1, len(sink.events) + 1)
    )
    assert [
        event.stage
        for event in sink.events
        if event.status is StageStatus.COMPLETED
    ] == [
        WorkflowStage.VALIDATING_INPUT,
        WorkflowStage.ANALYZING_REQUIREMENT,
        WorkflowStage.SEARCHING_KNOWLEDGE_BASE,
        WorkflowStage.RECONSTRUCTING_MAPPINGS,
        WorkflowStage.CALCULATING_CONFIDENCE,
        WorkflowStage.PERSISTING_REVISION,
        WorkflowStage.COMPLETED,
    ]
    assert {event.job_id for event in sink.events} == {"job-123"}
    assert {event.request_id for event in sink.events} == {request.request_id}
    assert all(
        event.duration_ms is not None
        for event in sink.events
        if event.status is StageStatus.COMPLETED
        and event.stage is not WorkflowStage.COMPLETED
    )


def test_failure_emits_one_safe_terminal_event(
    repository: SQLiteRequirementRepository,
) -> None:
    sink = MemoryStageEventSink()
    secret_requirement = "Build an ADC review GDA with Facility_secret."

    with pytest.raises(RuntimeError):
        asyncio.run(
            _service(repository, FailingAnalyzer()).analyze_initial(
                InitialAnalysisRequest(requirement=secret_requirement),
                event_sink=sink,
                job_id="job-failed",
            )
        )

    failures = [
        event
        for event in sink.events
        if event.status is StageStatus.FAILED
    ]
    assert len(failures) == 1
    assert failures[0].stage is WorkflowStage.FAILED
    assert failures[0].metadata == {
        "failed_stage": "analyzing_requirement",
        "exception_type": "RuntimeError",
    }
    assert secret_requirement not in failures[0].model_dump_json()

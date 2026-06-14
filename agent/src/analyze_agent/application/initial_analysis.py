"""Initial requirement analysis workflow."""

from __future__ import annotations

from uuid import uuid4

from analyze_agent.application.analysis_pipeline import AnalysisPipeline
from analyze_agent.application.language import validate_english_text
from analyze_agent.domain.models import AnalyzeResponse, InitialAnalysisRequest
from analyze_agent.ports.knowledge_reconstructor import KnowledgeReconstructor
from analyze_agent.ports.knowledge_retriever import KnowledgeBaseRetriever
from analyze_agent.ports.requirement_analyzer import RequirementAnalyzer
from analyze_agent.ports.requirement_repository import RequirementRepository
from analyze_agent.workflow_events import (
    StageEventSink,
    WorkflowStage,
    WorkflowTracker,
)


class InitialAnalysisService:
    def __init__(
        self,
        *,
        analyzer: RequirementAnalyzer,
        retriever: KnowledgeBaseRetriever,
        repository: RequirementRepository,
        model: str,
        prompt_version: str,
        knowledge_reconstructor: KnowledgeReconstructor | None = None,
    ) -> None:
        self._pipeline = AnalysisPipeline(
            analyzer=analyzer,
            retriever=retriever,
            model=model,
            prompt_version=prompt_version,
            knowledge_reconstructor=knowledge_reconstructor,
        )
        self._repository = repository

    async def analyze_initial(
        self,
        request: InitialAnalysisRequest,
        *,
        event_sink: StageEventSink | None = None,
        job_id: str | None = None,
    ) -> AnalyzeResponse:
        tracker = WorkflowTracker(
            job_id=job_id or str(request.request_id),
            request_id=request.request_id,
            sink=event_sink,
        )
        with tracker.stage(WorkflowStage.VALIDATING_INPUT):
            validate_english_text(request.requirement, field_name="requirement")
        requirement_id = uuid4()
        revision_id = uuid4()
        response = await self._pipeline.analyze(
            request_id=request.request_id,
            requirement_id=requirement_id,
            revision_id=revision_id,
            requirement=request.requirement,
            tracker=tracker,
        )
        with tracker.stage(WorkflowStage.PERSISTING_REVISION):
            self._repository.create_requirement(
                requirement_id=requirement_id,
                revision_id=revision_id,
                full_requirement=request.requirement,
                analyzed_requirement=response.analyzed_requirement.model_dump(
                    mode="json"
                ),
                output_snapshot=response.model_dump(mode="json"),
            )
        tracker.complete()
        return response

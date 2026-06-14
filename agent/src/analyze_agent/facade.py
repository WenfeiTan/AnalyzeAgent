"""Stable public facade for embedding Analyze Agent in other applications."""

from __future__ import annotations

from uuid import UUID

from analyze_agent.config import Settings, load_settings
from analyze_agent.domain.models import (
    AnalyzeResponse,
    InitialAnalysisRequest,
    KnowledgeChunk,
    UpdatedAnalysisRequest,
)
from analyze_agent.persistence.models import RequirementRevision
from analyze_agent.runtime import AnalyzeAgentRuntime, build_runtime
from analyze_agent.workflow_events import StageEventSink


class AnalyzeAgent:
    """Expose supported workflows without leaking internal module structure."""

    def __init__(self, runtime: AnalyzeAgentRuntime) -> None:
        self._runtime = runtime

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> AnalyzeAgent:
        resolved = settings or load_settings(require_api_key=True)
        return cls(build_runtime(resolved))

    async def analyze_initial(
        self,
        request: InitialAnalysisRequest,
        *,
        event_sink: StageEventSink | None = None,
        job_id: str | None = None,
    ) -> AnalyzeResponse:
        return await self._runtime.initial_service.analyze_initial(
            request,
            event_sink=event_sink,
            job_id=job_id,
        )

    async def analyze_update(
        self,
        request: UpdatedAnalysisRequest,
        *,
        event_sink: StageEventSink | None = None,
        job_id: str | None = None,
    ) -> AnalyzeResponse:
        return await self._runtime.updated_service.analyze_update(
            request,
            event_sink=event_sink,
            job_id=job_id,
        )

    async def search_knowledge_base(self, text: str) -> list[KnowledgeChunk]:
        return await self._runtime.retriever.search(text)

    def get_latest_revision(self, requirement_id: UUID) -> RequirementRevision:
        return self._runtime.repository.get_latest_revision(requirement_id)

    def list_revisions(self, requirement_id: UUID) -> list[RequirementRevision]:
        return self._runtime.repository.list_revisions(requirement_id)

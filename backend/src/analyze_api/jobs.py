"""In-process job execution and bounded stage-event retention."""

from __future__ import annotations

import asyncio
from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from analyze_agent import (
    AnalyzeAgent,
    AnalyzeResponse,
    ConfigurationError,
    DemoKnowledgeScenario,
    InitialAnalysisRequest,
    RequirementContext,
    StageEvent,
    StageEventSink,
    UpdatedAnalysisRequest,
)

from analyze_api.models import (
    ApiError,
    InitialJobRequest,
    JobResponse,
    JobStatus,
    JobSubmission,
    UpdateJobRequest,
)
from analyze_api.observability import WebMetrics, log_job_event


class AgentFactory(Protocol):
    def __call__(self, scenario: DemoKnowledgeScenario) -> AnalyzeAgent: ...


class JobCapacityError(RuntimeError):
    """Raised when all retained jobs are active and capacity is exhausted."""


@dataclass(slots=True)
class JobRecord:
    job_id: UUID
    request_id: UUID
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    request_payload: dict[str, Any]
    events: deque[StageEvent]
    result: AnalyzeResponse | None = None
    error: ApiError | None = None
    task: asyncio.Task[None] | None = field(default=None, repr=False)

    def response(self) -> JobResponse:
        return JobResponse(
            job_id=self.job_id,
            request_id=self.request_id,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
            request_payload=self.request_payload,
            result=self.result,
            error=self.error,
        )


class JobStore:
    def __init__(
        self,
        *,
        max_jobs: int,
        max_events_per_job: int,
        metrics: WebMetrics | None = None,
    ) -> None:
        self._max_jobs = max_jobs
        self._max_events = max_events_per_job
        self._jobs: OrderedDict[UUID, JobRecord] = OrderedDict()
        self.metrics = metrics or WebMetrics()

    def create(
        self,
        *,
        request_id: UUID,
        request_payload: dict[str, Any],
    ) -> JobRecord:
        self._evict_terminal_jobs()
        if len(self._jobs) >= self._max_jobs:
            raise JobCapacityError("Job capacity is currently exhausted.")
        now = datetime.now(UTC)
        record = JobRecord(
            job_id=uuid4(),
            request_id=request_id,
            status=JobStatus.QUEUED,
            created_at=now,
            updated_at=now,
            request_payload=request_payload,
            events=deque(maxlen=self._max_events),
        )
        self._jobs[record.job_id] = record
        self.metrics.increment("web_jobs.submitted")
        log_job_event(
            "web_job_submitted",
            job_id=str(record.job_id),
            request_id=str(record.request_id),
        )
        return record

    def get(self, job_id: UUID) -> JobRecord | None:
        return self._jobs.get(job_id)

    def append_event(self, job_id: UUID, event: StageEvent) -> None:
        record = self._jobs[job_id]
        record.events.append(event)
        record.updated_at = datetime.now(UTC)
        self.metrics.increment("web_stage_events.total")
        self.metrics.increment(
            f"web_stage_events.{event.stage.value}.{event.status.value}"
        )
        if event.duration_ms is not None:
            self.metrics.observe(
                f"web_stage_duration_ms.{event.stage.value}",
                event.duration_ms,
            )
        log_job_event(
            "web_stage_event",
            job_id=str(job_id),
            request_id=str(event.request_id),
            stage=event.stage.value,
            status=event.status.value,
            duration_ms=event.duration_ms,
        )

    def events_after(self, job_id: UUID, sequence: int) -> list[StageEvent]:
        return [
            event for event in self._jobs[job_id].events if event.sequence > sequence
        ]

    def _evict_terminal_jobs(self) -> None:
        while len(self._jobs) >= self._max_jobs:
            terminal_id = next(
                (
                    job_id
                    for job_id, record in self._jobs.items()
                    if record.status in {JobStatus.COMPLETED, JobStatus.FAILED}
                ),
                None,
            )
            if terminal_id is None:
                return
            self._jobs.pop(terminal_id)


class JobEventSink(StageEventSink):
    def __init__(self, store: JobStore, job_id: UUID) -> None:
        self._store = store
        self._job_id = job_id

    def emit(self, event: StageEvent) -> None:
        self._store.append_event(self._job_id, event)


class AnalysisJobService:
    def __init__(self, *, store: JobStore, agent_factory: AgentFactory) -> None:
        self.store = store
        self._agent_factory = agent_factory

    def submit_initial(self, payload: InitialJobRequest) -> JobSubmission:
        request = InitialAnalysisRequest(
            requirement=payload.requirement,
            context=RequirementContext(
                business_domain=payload.business_domain,
                target_gda=payload.target_gda,
            ),
        )
        record = self.store.create(
            request_id=request.request_id,
            request_payload=payload.model_dump(mode="json"),
        )
        record.task = asyncio.create_task(
            self._run_initial(record, request, payload.knowledge_base_scenario)
        )
        return JobSubmission(
            job_id=record.job_id,
            request_id=record.request_id,
            status=record.status,
        )

    def submit_update(self, payload: UpdateJobRequest) -> JobSubmission:
        request = UpdatedAnalysisRequest(
            requirement_id=payload.requirement_id,
            supplemental_information=payload.supplemental_information,
            search_feedback=payload.search_feedback,
        )
        record = self.store.create(
            request_id=request.request_id,
            request_payload=payload.model_dump(mode="json"),
        )
        record.task = asyncio.create_task(
            self._run_update(record, request, payload.knowledge_base_scenario)
        )
        return JobSubmission(
            job_id=record.job_id,
            request_id=record.request_id,
            status=record.status,
        )

    async def _run_initial(
        self,
        record: JobRecord,
        request: InitialAnalysisRequest,
        scenario: DemoKnowledgeScenario,
    ) -> None:
        await self._run(
            record,
            scenario,
            lambda agent, sink: agent.analyze_initial(
                request,
                event_sink=sink,
                job_id=str(record.job_id),
            ),
        )

    async def _run_update(
        self,
        record: JobRecord,
        request: UpdatedAnalysisRequest,
        scenario: DemoKnowledgeScenario,
    ) -> None:
        await self._run(
            record,
            scenario,
            lambda agent, sink: agent.analyze_update(
                request,
                event_sink=sink,
                job_id=str(record.job_id),
            ),
        )

    async def _run(
        self,
        record: JobRecord,
        scenario: DemoKnowledgeScenario,
        operation: Callable[
            [AnalyzeAgent, JobEventSink],
            Any,
        ],
    ) -> None:
        record.status = JobStatus.RUNNING
        record.updated_at = datetime.now(UTC)
        try:
            agent = self._agent_factory(scenario)
            response: AnalyzeResponse = await operation(
                agent,
                JobEventSink(self.store, record.job_id),
            )
        except ConfigurationError:
            self._fail(
                record,
                code="configuration_error",
                message="Gemini API key is not configured.",
            )
        except Exception as error:
            self._fail(
                record,
                code="workflow_error",
                message=_safe_workflow_message(error),
            )
        else:
            record.status = JobStatus.COMPLETED
            record.result = response
            record.updated_at = datetime.now(UTC)
            self.store.metrics.increment("web_jobs.completed")
            log_job_event(
                "web_job_completed",
                job_id=str(record.job_id),
                request_id=str(record.request_id),
            )

    def _fail(self, record: JobRecord, *, code: str, message: str) -> None:
        record.status = JobStatus.FAILED
        record.error = ApiError(code=code, message=message)
        record.updated_at = datetime.now(UTC)
        self.store.metrics.increment("web_jobs.failed")
        log_job_event(
            "web_job_failed",
            job_id=str(record.job_id),
            request_id=str(record.request_id),
            error_code=code,
        )


def _safe_workflow_message(error: Exception) -> str:
    name = type(error).__name__
    known = {
        "RequirementNotFoundError": "The selected requirement was not found.",
        "RevisionConflictError": "The requirement changed; reload and try again.",
        "UnsupportedRequirementLanguage": "Requirement text must be English.",
        "ModelAnalysisError": "Gemini could not produce a valid analysis.",
    }
    return known.get(name, "Analyze Agent could not complete this job.")

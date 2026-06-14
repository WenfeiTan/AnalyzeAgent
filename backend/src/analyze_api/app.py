"""FastAPI application for local Analyze Agent jobs."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from uuid import UUID

from analyze_agent import (
    AnalyzeAgentHistory,
    DemoKnowledgeScenario,
    RequirementNotFoundError,
    create_demo_agent,
    load_settings,
)
from fastapi import FastAPI, Header, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from analyze_api.config import ApiSettings
from analyze_api.jobs import (
    AgentFactory,
    AnalysisJobService,
    JobCapacityError,
    JobStore,
)
from analyze_api.models import (
    ApiError,
    ApiErrorResponse,
    ConfigurationResponse,
    InitialJobRequest,
    JobResponse,
    JobStatus,
    JobSubmission,
    MetricsResponse,
    RequirementSummaryResponse,
    RevisionResponse,
    StageEventResponse,
    UpdateJobRequest,
)
from analyze_api.observability import configure_web_observability

HistoryFactory = Callable[[], AnalyzeAgentHistory]


def create_app(
    *,
    agent_factory: AgentFactory | None = None,
    history_factory: HistoryFactory | None = None,
    settings: ApiSettings | None = None,
) -> FastAPI:
    api_settings = settings or ApiSettings.from_environment()
    agent_settings = load_settings(require_api_key=False)
    configure_web_observability(agent_settings.log_level)
    resolved_agent_factory = agent_factory or create_demo_agent
    resolved_history_factory = history_factory or AnalyzeAgentHistory.from_settings
    store = JobStore(
        max_jobs=api_settings.max_jobs,
        max_events_per_job=api_settings.max_events_per_job,
    )
    jobs = AnalysisJobService(store=store, agent_factory=resolved_agent_factory)

    app = FastAPI(
        title="Analyze Agent API",
        version="1.0.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(api_settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Last-Event-ID"],
    )
    app.state.jobs = jobs

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        del request, error
        return _error_response(
            status_code=422,
            code="validation_error",
            message="Request payload failed validation.",
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> JSONResponse:
        del request
        detail = error.detail
        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            payload = ApiError.model_validate(detail)
        else:
            payload = ApiError(code="http_error", message=str(detail))
        return JSONResponse(
            status_code=error.status_code,
            content=ApiErrorResponse(error=payload).model_dump(mode="json"),
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/metrics", response_model=MetricsResponse)
    async def metrics() -> MetricsResponse:
        return MetricsResponse.model_validate(store.metrics.snapshot())

    @app.get("/api/v1/configuration", response_model=ConfigurationResponse)
    async def configuration() -> ConfigurationResponse:
        return ConfigurationResponse(
            api_key_configured=bool(agent_settings.google_api_key),
            model=agent_settings.model,
            scenarios=list(DemoKnowledgeScenario),
        )

    @app.post(
        "/api/v1/jobs/initial",
        response_model=JobSubmission,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def submit_initial(payload: InitialJobRequest) -> JobSubmission:
        return _submit(lambda: jobs.submit_initial(payload))

    @app.post(
        "/api/v1/jobs/update",
        response_model=JobSubmission,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def submit_update(payload: UpdateJobRequest) -> JobSubmission:
        return _submit(lambda: jobs.submit_update(payload))

    @app.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
    async def get_job(job_id: UUID) -> JobResponse:
        record = store.get(job_id)
        if record is None:
            raise _http_exception(404, "job_not_found", "Job not found.")
        return record.response()

    @app.get(
        "/api/v1/jobs/{job_id}/events",
        responses={
            200: {
                "model": StageEventResponse,
                "description": "Server-Sent Events containing stage and job payloads.",
                "content": {"text/event-stream": {}},
            }
        },
    )
    async def stream_events(
        job_id: UUID,
        after: int = Query(default=0, ge=0),
        last_event_id: str | None = Header(
            default=None,
            alias="Last-Event-ID",
        ),
    ) -> StreamingResponse:
        if store.get(job_id) is None:
            raise _http_exception(404, "job_not_found", "Job not found.")
        sequence = _resume_sequence(after, last_event_id)

        async def event_stream():
            current = sequence
            while True:
                record = store.get(job_id)
                if record is None:
                    return
                events = store.events_after(job_id, current)
                for event in events:
                    current = event.sequence
                    yield _sse(event.sequence, "stage", event.model_dump(mode="json"))
                if (
                    record.status in {JobStatus.COMPLETED, JobStatus.FAILED}
                    and not store.events_after(job_id, current)
                ):
                    yield _sse(
                        current + 1,
                        "job",
                        record.response().model_dump(mode="json"),
                    )
                    return
                await asyncio.sleep(api_settings.event_poll_seconds)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get(
        "/api/v1/requirements",
        response_model=list[RequirementSummaryResponse],
    )
    async def list_requirements() -> list[RequirementSummaryResponse]:
        history = resolved_history_factory()
        return [
            RequirementSummaryResponse.model_validate(item, from_attributes=True)
            for item in history.list_requirements()
        ]

    @app.get(
        "/api/v1/requirements/{requirement_id}/latest",
        response_model=RevisionResponse,
    )
    async def latest_revision(requirement_id: UUID) -> RevisionResponse:
        try:
            revision = resolved_history_factory().get_latest_revision(requirement_id)
        except RequirementNotFoundError as error:
            raise _http_exception(
                404,
                "requirement_not_found",
                "Requirement not found.",
            ) from error
        return _revision_response(revision)

    @app.get(
        "/api/v1/requirements/{requirement_id}/revisions",
        response_model=list[RevisionResponse],
    )
    async def list_revisions(requirement_id: UUID) -> list[RevisionResponse]:
        try:
            revisions = resolved_history_factory().list_revisions(requirement_id)
        except RequirementNotFoundError as error:
            raise _http_exception(
                404,
                "requirement_not_found",
                "Requirement not found.",
            ) from error
        return [_revision_response(item) for item in revisions]

    return app


def _submit(operation: Callable[[], JobSubmission]) -> JobSubmission:
    try:
        return operation()
    except JobCapacityError as error:
        raise _http_exception(
            503,
            "job_capacity_exhausted",
            str(error),
        ) from error


def _revision_response(revision) -> RevisionResponse:
    payload = revision.model_dump(mode="json")
    return RevisionResponse.model_validate(payload)


def _resume_sequence(after: int, last_event_id: str | None) -> int:
    if last_event_id is None:
        return after
    try:
        return max(after, int(last_event_id))
    except ValueError as error:
        raise _http_exception(
            400,
            "invalid_event_cursor",
            "Last-Event-ID must be an integer.",
        ) from error


def _sse(sequence: int, event: str, payload: dict) -> str:
    return (
        f"id: {sequence}\n"
        f"event: {event}\n"
        f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"
    )


def _http_exception(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=ApiError(code=code, message=message).model_dump(mode="json"),
    )


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    payload = ApiErrorResponse(error=ApiError(code=code, message=message))
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
    )


app = create_app()

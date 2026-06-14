"""Versioned HTTP contracts for the Analyze Agent demo API."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from analyze_agent import (
    AnalyzeResponse,
    DemoKnowledgeScenario,
    SearchFeedback,
    StageStatus,
    WorkflowStage,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class InitialJobRequest(ApiModel):
    requirement: str = Field(min_length=1)
    business_domain: str | None = None
    target_gda: str | None = None
    knowledge_base_scenario: DemoKnowledgeScenario = DemoKnowledgeScenario.EMPTY


class UpdateJobRequest(ApiModel):
    requirement_id: UUID
    supplemental_information: str | None = None
    search_feedback: list[SearchFeedback] = Field(default_factory=list)
    knowledge_base_scenario: DemoKnowledgeScenario = DemoKnowledgeScenario.EMPTY

    @model_validator(mode="after")
    def require_update_content(self) -> UpdateJobRequest:
        if not self.supplemental_information and not self.search_feedback:
            raise ValueError(
                "supplemental_information or search_feedback is required"
            )
        return self


class JobSubmission(ApiModel):
    job_id: UUID
    request_id: UUID
    status: JobStatus


class ApiError(ApiModel):
    code: str
    message: str


class ApiErrorResponse(ApiModel):
    error: ApiError


class JobResponse(ApiModel):
    job_id: UUID
    request_id: UUID
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    request_payload: dict[str, Any]
    result: AnalyzeResponse | None = None
    error: ApiError | None = None


class ConfigurationResponse(ApiModel):
    api_key_configured: bool
    model: str
    knowledge_base_provider: str = "fake"
    scenarios: list[DemoKnowledgeScenario]


class StageEventResponse(ApiModel):
    job_id: str
    request_id: UUID
    stage: WorkflowStage
    status: StageStatus
    sequence: int
    timestamp: datetime
    duration_ms: float | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict
    )


class MetricsResponse(ApiModel):
    counters: dict[str, int]
    observations: dict[str, list[float]]


class RequirementSummaryResponse(ApiModel):
    requirement_id: UUID
    latest_revision_number: int
    summary: str
    created_at: datetime
    updated_at: datetime


class RevisionResponse(ApiModel):
    requirement_id: UUID
    revision_id: UUID
    revision_number: int
    full_requirement: str
    supplemental_information: str | None
    analyzed_requirement: dict[str, Any] | None
    changes: list[dict[str, Any]]
    feedback: list[dict[str, Any]]
    output_snapshot: dict[str, Any] | None
    created_at: datetime

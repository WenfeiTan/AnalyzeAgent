"""Records returned by requirement repositories."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from analyze_agent.domain.models import RequirementChange, SearchFeedback


class RequirementRevision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requirement_id: UUID
    revision_id: UUID
    revision_number: int = Field(ge=1)
    full_requirement: str = Field(min_length=1)
    supplemental_information: str | None = None
    analyzed_requirement: dict[str, Any] | None = None
    changes: list[RequirementChange] = Field(default_factory=list)
    feedback: list[SearchFeedback] = Field(default_factory=list)
    output_snapshot: dict[str, Any] | None = None
    created_at: datetime


class RequirementSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requirement_id: UUID
    latest_revision_number: int = Field(ge=1)
    summary: str
    created_at: datetime
    updated_at: datetime

"""Persistence port for requirements and immutable revisions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol
from uuid import UUID

from analyze_agent.domain.models import RequirementChange, SearchFeedback
from analyze_agent.persistence.models import RequirementRevision, RequirementSummary


class RequirementRepository(Protocol):
    def create_requirement(
        self,
        *,
        requirement_id: UUID | None = None,
        revision_id: UUID | None = None,
        full_requirement: str,
        analyzed_requirement: Mapping[str, Any] | None = None,
        feedback: Sequence[SearchFeedback] = (),
        output_snapshot: Mapping[str, Any] | None = None,
    ) -> RequirementRevision: ...

    def get_latest_revision(self, requirement_id: UUID) -> RequirementRevision: ...

    def list_revisions(self, requirement_id: UUID) -> list[RequirementRevision]: ...

    def list_requirements(self) -> list[RequirementSummary]: ...

    def append_revision(
        self,
        *,
        requirement_id: UUID,
        expected_base_revision_number: int,
        full_requirement: str,
        supplemental_information: str | None,
        analyzed_requirement: Mapping[str, Any] | None = None,
        changes: Sequence[RequirementChange] = (),
        feedback: Sequence[SearchFeedback] = (),
        output_snapshot: Mapping[str, Any] | None = None,
    ) -> RequirementRevision: ...

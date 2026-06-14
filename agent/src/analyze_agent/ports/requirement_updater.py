"""Boundary for producing a complete updated requirement."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from analyze_agent.domain.models import RequirementUpdateSignals, SearchFeedback


class RequirementUpdater(Protocol):
    async def update(
        self,
        *,
        previous_requirement: str,
        supplemental_information: str | None,
        feedback: list[SearchFeedback],
        previous_output: Mapping[str, Any] | None,
    ) -> RequirementUpdateSignals: ...


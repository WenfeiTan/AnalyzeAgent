"""Boundary for structured requirement analysis."""

from __future__ import annotations

from typing import Protocol

from analyze_agent.domain.models import RequirementAnalysisSignals


class RequirementAnalyzer(Protocol):
    async def analyze(self, requirement: str) -> RequirementAnalysisSignals: ...


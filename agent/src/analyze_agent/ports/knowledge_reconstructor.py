"""Boundary for reconstructing mapping candidates from retrieved chunks."""

from __future__ import annotations

from typing import Protocol

from analyze_agent.domain.models import (
    AnalyzedRequirement,
    KnowledgeChunk,
    KnowledgeReuseSignals,
)


class KnowledgeReconstructor(Protocol):
    async def reconstruct(
        self,
        *,
        requirement: str,
        analyzed_requirement: AnalyzedRequirement,
        chunks: list[KnowledgeChunk],
    ) -> KnowledgeReuseSignals: ...


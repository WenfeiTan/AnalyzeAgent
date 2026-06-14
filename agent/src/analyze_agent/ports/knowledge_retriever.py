"""Stable boundary for external Knowledge Base retrieval."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from analyze_agent.domain.models import KnowledgeChunk


@runtime_checkable
class KnowledgeBaseRetriever(Protocol):
    """Retrieve normalized Knowledge Base chunks for a text query."""

    async def search(self, text: str) -> list[KnowledgeChunk]: ...


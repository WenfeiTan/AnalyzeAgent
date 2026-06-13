"""Stable async tool functions registered with the Google ADK agent."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from analyze_agent.domain.models import (
    InitialAnalysisRequest,
    RequirementContext,
    SearchFeedback,
    UpdatedAnalysisRequest,
)
from analyze_agent.runtime import get_runtime


async def analyze_initial(
    requirement: str,
    business_domain: str | None = None,
    target_gda: str | None = None,
) -> dict[str, Any]:
    """Analyze a new English Asset Discovery requirement."""

    request = InitialAnalysisRequest(
        requirement=requirement,
        context=RequirementContext(
            business_domain=business_domain,
            target_gda=target_gda,
        ),
    )
    response = await get_runtime().initial_service.analyze_initial(request)
    return response.model_dump(mode="json")


async def analyze_update(
    requirement_id: str,
    supplemental_information: str | None = None,
    search_feedback: list[SearchFeedback] | None = None,
) -> dict[str, Any]:
    """Update a stored requirement using English supplemental information and feedback."""

    request = UpdatedAnalysisRequest(
        requirement_id=UUID(requirement_id),
        supplemental_information=supplemental_information,
        search_feedback=search_feedback or [],
    )
    response = await get_runtime().updated_service.analyze_update(request)
    return response.model_dump(mode="json")


async def search_knowledge_base(text: str) -> dict[str, Any]:
    """Return normalized chunks from the configured Knowledge Base retriever."""

    chunks = await get_runtime().retriever.search(text)
    return {
        "query_text": text,
        "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
    }


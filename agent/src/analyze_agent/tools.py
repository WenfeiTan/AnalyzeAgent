"""Stable async tool functions registered with the Google ADK agent."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any
from uuid import UUID

from analyze_agent.domain.models import (
    InitialAnalysisRequest,
    RequirementContext,
    SearchFeedback,
    UpdatedAnalysisRequest,
)
from analyze_agent.observability import METRICS, bind_correlation, log_event
from analyze_agent.runtime import get_runtime

_LOGGER = logging.getLogger(__name__)


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
    started_at = perf_counter()
    METRICS.increment("tool_calls.analyze_initial")
    with bind_correlation(request_id=str(request.request_id)):
        log_event(_LOGGER, "analyze_initial.started")
        try:
            response = await get_runtime().initial_service.analyze_initial(request)
        except Exception:
            METRICS.increment("tool_failures.analyze_initial")
            _LOGGER.exception("analyze_initial.failed")
            raise
        duration_ms = (perf_counter() - started_at) * 1000
        METRICS.observe("tool_duration_ms.analyze_initial", duration_ms)
        with bind_correlation(
            requirement_id=str(response.requirement_id),
            revision_id=str(response.revision_id),
        ):
            log_event(
                _LOGGER,
                "analyze_initial.completed",
                duration_ms=round(duration_ms, 3),
            )
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
    started_at = perf_counter()
    METRICS.increment("tool_calls.analyze_update")
    with bind_correlation(
        request_id=str(request.request_id),
        requirement_id=str(request.requirement_id),
    ):
        log_event(_LOGGER, "analyze_update.started")
        try:
            response = await get_runtime().updated_service.analyze_update(request)
        except Exception:
            METRICS.increment("tool_failures.analyze_update")
            _LOGGER.exception("analyze_update.failed")
            raise
        duration_ms = (perf_counter() - started_at) * 1000
        METRICS.observe("tool_duration_ms.analyze_update", duration_ms)
        with bind_correlation(revision_id=str(response.revision_id)):
            log_event(
                _LOGGER,
                "analyze_update.completed",
                duration_ms=round(duration_ms, 3),
            )
        return response.model_dump(mode="json")


async def search_knowledge_base(text: str) -> dict[str, Any]:
    """Return normalized chunks from the configured Knowledge Base retriever."""

    started_at = perf_counter()
    METRICS.increment("tool_calls.search_knowledge_base")
    log_event(_LOGGER, "search_knowledge_base.started")
    try:
        chunks = await get_runtime().retriever.search(text)
    except Exception:
        METRICS.increment("tool_failures.search_knowledge_base")
        _LOGGER.exception("search_knowledge_base.failed")
        raise
    duration_ms = (perf_counter() - started_at) * 1000
    METRICS.observe("tool_duration_ms.search_knowledge_base", duration_ms)
    log_event(
        _LOGGER,
        "search_knowledge_base.completed",
        duration_ms=round(duration_ms, 3),
        chunk_count=len(chunks),
    )
    return {
        "query_text": text,
        "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
    }

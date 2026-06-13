"""Initial requirement analysis workflow."""

from __future__ import annotations

import re
from time import perf_counter
from uuid import uuid4

from analyze_agent.application.language import validate_english_text
from analyze_agent.domain.confidence import (
    ConfidenceSignals,
    SuggestionKind,
    calculate_confidence,
)
from analyze_agent.domain.models import (
    AnalyzeResponse,
    ClearFieldSuggestion,
    Evidence,
    EvidenceType,
    InitialAnalysisRequest,
    KeywordAnalysisSignal,
    KeywordStrength,
    KeywordSuggestion,
    ProcessingTrace,
    SuggestionOrigin,
)
from analyze_agent.ports.knowledge_retriever import KnowledgeBaseRetriever
from analyze_agent.ports.requirement_analyzer import RequirementAnalyzer
from analyze_agent.ports.requirement_repository import RequirementRepository
from analyze_agent.ports.retriever_errors import KnowledgeRetrievalError

_NORMALIZE_SEPARATOR = re.compile(r"[\s-]+")


class InitialAnalysisService:
    def __init__(
        self,
        *,
        analyzer: RequirementAnalyzer,
        retriever: KnowledgeBaseRetriever,
        repository: RequirementRepository,
        model: str,
        prompt_version: str,
    ) -> None:
        self._analyzer = analyzer
        self._retriever = retriever
        self._repository = repository
        self._model = model
        self._prompt_version = prompt_version

    async def analyze_initial(
        self,
        request: InitialAnalysisRequest,
    ) -> AnalyzeResponse:
        started_at = perf_counter()
        validate_english_text(request.requirement, field_name="requirement")

        signals = await self._analyzer.analyze(request.requirement)
        knowledge_query = request.requirement
        warnings: list[str] = []
        try:
            await self._retriever.search(knowledge_query)
        except KnowledgeRetrievalError as error:
            warnings.append(str(error))

        clear_fields = [
            ClearFieldSuggestion(
                name=field.name,
                confidence=_required_confidence(
                    ConfidenceSignals(
                        kind=SuggestionKind.FIELD,
                        explicit_requirement=True,
                    )
                ),
                origin=SuggestionOrigin.EXPLICIT_REQUIREMENT,
                priority=index,
                normalized_terms=field.normalized_terms
                or [_normalize_field(field.name)],
                evidence=[
                    Evidence(
                        type=EvidenceType.REQUIREMENT_SPAN,
                        reference=field.name,
                        excerpt=field.requirement_excerpt,
                    )
                ],
                rationale="Field name is explicitly stated in the requirement.",
            )
            for index, field in enumerate(signals.clear_fields, start=1)
        ]

        keyword_priority_start = len(clear_fields) + 1
        keywords = [
            _build_keyword(
                keyword,
                priority=keyword_priority_start + index,
            )
            for index, keyword in enumerate(signals.keywords)
        ]

        requirement_id = uuid4()
        revision_id = uuid4()
        response = AnalyzeResponse(
            request_id=request.request_id,
            requirement_id=requirement_id,
            revision_id=revision_id,
            analyzed_requirement=signals.analyzed_requirement,
            clear_fields=clear_fields,
            keywords=keywords,
            warnings=[*signals.ambiguities, *warnings],
            trace=ProcessingTrace(
                prompt_version=self._prompt_version,
                model=self._model,
                knowledge_base_queries=[knowledge_query],
                processing_time_ms=max(
                    0,
                    round((perf_counter() - started_at) * 1000),
                ),
            ),
        )
        self._repository.create_requirement(
            requirement_id=requirement_id,
            revision_id=revision_id,
            full_requirement=request.requirement,
            analyzed_requirement=signals.analyzed_requirement.model_dump(mode="json"),
            output_snapshot=response.model_dump(mode="json"),
        )
        return response


def _build_keyword(
    keyword: KeywordAnalysisSignal,
    *,
    priority: int,
) -> KeywordSuggestion:
    confidence = _required_confidence(
        ConfidenceSignals(
            kind=SuggestionKind.KEYWORD,
            core_keyword=keyword.strength is KeywordStrength.CORE,
            inferred_keyword=keyword.strength is KeywordStrength.EXPANDED,
        )
    )
    return KeywordSuggestion(
        name=keyword.name,
        confidence=confidence,
        origin=SuggestionOrigin.REQUIREMENT_ANALYSIS,
        priority=priority,
        normalized_terms=keyword.normalized_terms or [keyword.name],
        rationale=keyword.rationale,
    )


def _required_confidence(signals: ConfidenceSignals):
    confidence = calculate_confidence(signals)
    if confidence is None:
        raise RuntimeError("Non-rejected initial suggestion produced no confidence.")
    return confidence


def _normalize_field(name: str) -> str:
    return _NORMALIZE_SEPARATOR.sub("_", name.strip()).lower()


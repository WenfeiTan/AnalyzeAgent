"""Shared analysis pipeline without persistence side effects."""

from __future__ import annotations

import re
from time import perf_counter
from uuid import UUID

from analyze_agent.application.knowledge_reuse import build_reused_mappings
from analyze_agent.application.language import validate_english_text
from analyze_agent.domain.confidence import (
    ConfidenceSignals,
    SuggestionKind,
    calculate_confidence,
)
from analyze_agent.domain.models import (
    AnalyzeResponse,
    ChangeSummary,
    ClearFieldSuggestion,
    Evidence,
    EvidenceType,
    KeywordAnalysisSignal,
    KeywordStrength,
    KeywordSuggestion,
    KnowledgeChunk,
    ProcessingTrace,
    SuggestionOrigin,
)
from analyze_agent.ports.knowledge_reconstructor import KnowledgeReconstructor
from analyze_agent.ports.knowledge_retriever import KnowledgeBaseRetriever
from analyze_agent.ports.reconstructor_errors import KnowledgeReconstructionError
from analyze_agent.ports.requirement_analyzer import RequirementAnalyzer
from analyze_agent.ports.retriever_errors import KnowledgeRetrievalError

_NORMALIZE_SEPARATOR = re.compile(r"[\s-]+")


class AnalysisPipeline:
    def __init__(
        self,
        *,
        analyzer: RequirementAnalyzer,
        retriever: KnowledgeBaseRetriever,
        model: str,
        prompt_version: str,
        knowledge_reconstructor: KnowledgeReconstructor | None = None,
    ) -> None:
        self._analyzer = analyzer
        self._retriever = retriever
        self._model = model
        self._prompt_version = prompt_version
        self._knowledge_reconstructor = knowledge_reconstructor

    async def analyze(
        self,
        *,
        request_id: UUID,
        requirement_id: UUID,
        revision_id: UUID,
        requirement: str,
        change_summary: ChangeSummary | None = None,
    ) -> AnalyzeResponse:
        started_at = perf_counter()
        validate_english_text(requirement, field_name="requirement")

        signals = await self._analyzer.analyze(requirement)
        warnings: list[str] = []
        chunks: list[KnowledgeChunk] = []
        try:
            chunks = await self._retriever.search(requirement)
        except KnowledgeRetrievalError as error:
            warnings.append(str(error))

        reused_mappings = []
        if chunks and self._knowledge_reconstructor is not None:
            try:
                reuse_signals = await self._knowledge_reconstructor.reconstruct(
                    requirement=requirement,
                    analyzed_requirement=signals.analyzed_requirement,
                    chunks=chunks,
                )
                reused_mappings = build_reused_mappings(
                    candidates=reuse_signals.candidates,
                    chunks=chunks,
                    negative_constraints=(
                        signals.analyzed_requirement.negative_constraints
                    ),
                )
            except KnowledgeReconstructionError as error:
                warnings.append(str(error))

        clear_field_priority_start = len(reused_mappings) + 1
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
                priority=clear_field_priority_start + index,
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
            for index, field in enumerate(signals.clear_fields)
        ]
        keyword_priority_start = len(reused_mappings) + len(clear_fields) + 1
        keywords = [
            _build_keyword(
                keyword,
                priority=keyword_priority_start + index,
            )
            for index, keyword in enumerate(signals.keywords)
        ]
        return AnalyzeResponse(
            request_id=request_id,
            requirement_id=requirement_id,
            revision_id=revision_id,
            analyzed_requirement=signals.analyzed_requirement,
            clear_fields=clear_fields,
            keywords=keywords,
            reused_mappings=reused_mappings,
            change_summary=change_summary,
            warnings=[*signals.ambiguities, *warnings],
            trace=ProcessingTrace(
                prompt_version=self._prompt_version,
                model=self._model,
                knowledge_base_queries=[requirement],
                processing_time_ms=max(
                    0,
                    round((perf_counter() - started_at) * 1000),
                ),
            ),
        )


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
        raise RuntimeError("Non-rejected suggestion produced no confidence.")
    return confidence


def _normalize_field(name: str) -> str:
    return _NORMALIZE_SEPARATOR.sub("_", name.strip()).lower()


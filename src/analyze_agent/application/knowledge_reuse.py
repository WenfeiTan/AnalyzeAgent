"""Deterministic verification and conversion of reconstructed mappings."""

from __future__ import annotations

import json
import re

from analyze_agent.domain.confidence import (
    ConfidenceSignals,
    SuggestionKind,
    calculate_confidence,
)
from analyze_agent.domain.models import (
    Evidence,
    EvidenceType,
    KnowledgeChunk,
    KnowledgeMappingCandidate,
    ReusedMapping,
)

_SUCCESS_MARKER = re.compile(r"\bsuccess(?:ful|fully)?\b", re.IGNORECASE)


def build_reused_mappings(
    *,
    candidates: list[KnowledgeMappingCandidate],
    chunks: list[KnowledgeChunk],
    negative_constraints: list[str],
) -> list[ReusedMapping]:
    chunks_by_id = {
        chunk.chunk_id: chunk for chunk in chunks if chunk.chunk_id is not None
    }
    negative = {item.casefold() for item in negative_constraints}
    results: list[ReusedMapping] = []
    seen_fields: set[str] = set()

    for candidate in candidates:
        normalized_field = candidate.field_name.casefold()
        if normalized_field in seen_fields or normalized_field in negative:
            continue
        supporting = _supporting_chunks(candidate, chunks_by_id)
        if not _candidate_is_reusable(candidate, supporting):
            continue

        confidence = calculate_confidence(
            ConfidenceSignals(
                kind=SuggestionKind.MAPPING,
                verified_success_case=True,
            )
        )
        if confidence is None:
            continue
        results.append(
            ReusedMapping(
                field_name=candidate.field_name,
                confidence=confidence,
                priority=len(results) + 1,
                sources=candidate.sources,
                evidence=[
                    Evidence(
                        type=EvidenceType.KNOWLEDGE_CHUNK,
                        reference=chunk.chunk_id or "",
                        excerpt=chunk.text,
                    )
                    for chunk in supporting
                ],
                rationale=candidate.rationale,
            )
        )
        seen_fields.add(normalized_field)

    return results


def _supporting_chunks(
    candidate: KnowledgeMappingCandidate,
    chunks_by_id: dict[str, KnowledgeChunk],
) -> list[KnowledgeChunk]:
    if not candidate.supporting_chunk_ids:
        return []
    if any(chunk_id not in chunks_by_id for chunk_id in candidate.supporting_chunk_ids):
        return []
    return [chunks_by_id[chunk_id] for chunk_id in candidate.supporting_chunk_ids]


def _candidate_is_reusable(
    candidate: KnowledgeMappingCandidate,
    supporting: list[KnowledgeChunk],
) -> bool:
    if not supporting or not candidate.sources:
        return False
    if not (
        candidate.success_case_confirmed
        and candidate.intent_match
        and candidate.domain_compatible
        and candidate.business_definition_compatible
        and not candidate.context_conflict
    ):
        return False
    if not _has_success_evidence(supporting):
        return False

    corpus = " ".join(
        f"{chunk.text} {json.dumps(chunk.metadata, ensure_ascii=True)}"
        for chunk in supporting
    ).casefold()
    if candidate.field_name.casefold() not in corpus:
        return False
    return all(_source_is_supported(source, corpus) for source in candidate.sources)


def _has_success_evidence(chunks: list[KnowledgeChunk]) -> bool:
    return any(
        str(chunk.metadata.get("case_status", "")).casefold() == "success"
        or _SUCCESS_MARKER.search(chunk.text)
        for chunk in chunks
    )


def _source_is_supported(source, corpus: str) -> bool:
    attribute_identities = [
        source.attribute.attribute_id,
        source.attribute.attribute_name,
    ]
    asset_identities = [
        source.asset.asset_id,
        source.asset.asset_name,
    ]
    return _has_identity(attribute_identities, corpus) and _has_identity(
        asset_identities, corpus
    )


def _has_identity(identities: list[str | None], corpus: str) -> bool:
    return any(identity and identity.casefold() in corpus for identity in identities)

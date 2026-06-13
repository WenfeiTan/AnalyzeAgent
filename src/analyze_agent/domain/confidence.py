"""Deterministic confidence scoring for search suggestions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator

from analyze_agent.domain.models import Confidence, ConfidenceLevel


class SuggestionKind(StrEnum):
    FIELD = "field"
    KEYWORD = "keyword"
    MAPPING = "mapping"


@dataclass(frozen=True, slots=True)
class ConfidencePolicy:
    verified_mapping_base: float = 0.90
    explicit_field_base: float = 0.70
    core_keyword_base: float = 0.60
    inferred_keyword_base: float = 0.40
    user_confirmation_bonus: float = 0.10
    incomplete_evidence_penalty: float = 0.15
    context_conflict_penalty: float = 0.25
    ambiguity_penalty: float = 0.10
    high_threshold: float = 0.85
    medium_threshold: float = 0.55


DEFAULT_CONFIDENCE_POLICY = ConfidencePolicy()


class ConfidenceSignals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: SuggestionKind
    verified_success_case: bool = False
    explicit_requirement: bool = False
    core_keyword: bool = False
    inferred_keyword: bool = False
    user_confirmed: bool = False
    user_rejected: bool = False
    incomplete_evidence: bool = False
    context_conflict: bool = False
    ambiguous: bool = False

    @model_validator(mode="after")
    def validate_base_signal(self) -> ConfidenceSignals:
        if self.kind is SuggestionKind.MAPPING and not self.verified_success_case:
            raise ValueError("mapping confidence requires a verified success case")
        if self.kind is SuggestionKind.FIELD and not self.explicit_requirement:
            raise ValueError("field confidence requires an explicit requirement signal")
        if self.kind is SuggestionKind.KEYWORD:
            if self.core_keyword == self.inferred_keyword:
                raise ValueError(
                    "keyword confidence requires exactly one keyword strength signal"
                )
        return self


def calculate_confidence(
    signals: ConfidenceSignals,
    policy: ConfidencePolicy = DEFAULT_CONFIDENCE_POLICY,
) -> Confidence | None:
    """Calculate final confidence, or exclude a user-rejected candidate."""

    if signals.user_rejected:
        return None

    score = _base_score(signals, policy)
    if signals.user_confirmed:
        score += policy.user_confirmation_bonus
    if signals.incomplete_evidence:
        score -= policy.incomplete_evidence_penalty
    if signals.context_conflict:
        score -= policy.context_conflict_penalty
    if signals.ambiguous:
        score -= policy.ambiguity_penalty

    bounded_score = round(min(1.0, max(0.0, score)), 4)
    return Confidence(
        level=_level_for_score(bounded_score, policy),
        score=bounded_score,
    )


def _base_score(signals: ConfidenceSignals, policy: ConfidencePolicy) -> float:
    if signals.kind is SuggestionKind.MAPPING:
        return policy.verified_mapping_base
    if signals.kind is SuggestionKind.FIELD:
        return policy.explicit_field_base
    if signals.core_keyword:
        return policy.core_keyword_base
    return policy.inferred_keyword_base


def _level_for_score(
    score: float,
    policy: ConfidencePolicy,
) -> ConfidenceLevel:
    if score >= policy.high_threshold:
        return ConfidenceLevel.HIGH
    if score >= policy.medium_threshold:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


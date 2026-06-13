"""Pydantic contracts for Analyze Agent inputs, outputs, and model signals."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FeedbackDecision(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"


class FeedbackTargetType(StrEnum):
    ASSET = "asset"
    ATTRIBUTE = "attribute"
    FIELD_MAPPING = "field_mapping"


class SuggestionOrigin(StrEnum):
    SUCCESS_CASE = "success_case"
    EXPLICIT_REQUIREMENT = "explicit_requirement"
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    USER_FEEDBACK = "user_feedback"


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SearchStrategy(StrEnum):
    EXACT_FIELD_FIRST = "exact_field_first"
    SEMANTIC_KEYWORD = "semantic_keyword"
    SOURCE_HINT_FIRST = "source_hint_first"


class EvidenceType(StrEnum):
    REQUIREMENT_SPAN = "requirement_span"
    KNOWLEDGE_CHUNK = "knowledge_chunk"
    USER_FEEDBACK = "user_feedback"


class ChangeAction(StrEnum):
    ADD = "add"
    CORRECT = "correct"
    REMOVE = "remove"
    CONFIRM = "confirm"
    REJECT = "reject"


class KeywordStrength(StrEnum):
    CORE = "core"
    EXPANDED = "expanded"


class RequirementContext(ContractModel):
    business_domain: str | None = None
    target_gda: str | None = None
    locale: Literal["en"] = "en"
    caller: str = "asset-discovery-orchestrator"


class InitialAnalysisRequest(ContractModel):
    request_id: UUID = Field(default_factory=uuid4)
    requirement: str = Field(min_length=1)
    context: RequirementContext = Field(default_factory=RequirementContext)


class AssetReference(ContractModel):
    asset_id: str | None = None
    asset_name: str | None = None
    source_system: str | None = None

    @model_validator(mode="after")
    def require_identity(self) -> AssetReference:
        if not self.asset_id and not self.asset_name:
            raise ValueError("asset_id or asset_name is required")
        return self


class AttributeReference(ContractModel):
    attribute_id: str | None = None
    attribute_name: str | None = None

    @model_validator(mode="after")
    def require_identity(self) -> AttributeReference:
        if not self.attribute_id and not self.attribute_name:
            raise ValueError("attribute_id or attribute_name is required")
        return self


class SearchFeedback(ContractModel):
    candidate_id: str = Field(min_length=1)
    target_type: FeedbackTargetType
    decision: FeedbackDecision
    reason: str | None = None
    field_name: str | None = None
    asset: AssetReference | None = None
    attribute: AttributeReference | None = None

    @model_validator(mode="after")
    def validate_target_payload(self) -> SearchFeedback:
        if self.target_type is FeedbackTargetType.ASSET and self.asset is None:
            raise ValueError("asset feedback requires asset")
        if self.target_type is FeedbackTargetType.ATTRIBUTE and self.attribute is None:
            raise ValueError("attribute feedback requires attribute")
        if self.target_type is FeedbackTargetType.FIELD_MAPPING:
            if not self.field_name or self.asset is None or self.attribute is None:
                raise ValueError(
                    "field_mapping feedback requires field_name, asset, and attribute"
                )
        return self


class UpdatedAnalysisRequest(ContractModel):
    request_id: UUID = Field(default_factory=uuid4)
    requirement_id: UUID
    supplemental_information: str | None = None
    search_feedback: list[SearchFeedback] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_update_content(self) -> UpdatedAnalysisRequest:
        if not self.supplemental_information and not self.search_feedback:
            raise ValueError(
                "supplemental_information or search_feedback is required"
            )
        return self


class AnalyzedRequirement(ContractModel):
    summary: str = Field(min_length=1)
    business_goal: str = Field(min_length=1)
    domain_context: list[str] = Field(default_factory=list)
    target_output: str = "GDA"
    constraints: list[str] = Field(default_factory=list)
    negative_constraints: list[str] = Field(default_factory=list)


class Evidence(ContractModel):
    type: EvidenceType
    reference: str = Field(min_length=1)
    excerpt: str | None = None


class Confidence(ContractModel):
    level: ConfidenceLevel
    score: float = Field(ge=0.0, le=1.0)


class ClearFieldSuggestion(ContractModel):
    suggestion_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1)
    confidence: Confidence
    origin: SuggestionOrigin
    priority: int = Field(ge=1)
    search_strategy: Literal[SearchStrategy.EXACT_FIELD_FIRST] = (
        SearchStrategy.EXACT_FIELD_FIRST
    )
    normalized_terms: list[str] = Field(default_factory=list)
    source_hints: list[SourceAttributeMapping] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    rationale: str = Field(min_length=1)


class KeywordSuggestion(ContractModel):
    suggestion_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1)
    confidence: Confidence
    origin: SuggestionOrigin
    priority: int = Field(ge=1)
    search_strategy: Literal[SearchStrategy.SEMANTIC_KEYWORD] = (
        SearchStrategy.SEMANTIC_KEYWORD
    )
    normalized_terms: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    rationale: str = Field(min_length=1)


class SourceAttributeMapping(ContractModel):
    attribute: AttributeReference
    asset: AssetReference


class KnowledgeMappingCandidate(ContractModel):
    field_name: str = Field(min_length=1)
    business_definition: str | None = None
    sources: list[SourceAttributeMapping] = Field(default_factory=list)
    supporting_chunk_ids: list[str] = Field(default_factory=list)
    success_case_confirmed: bool
    intent_match: bool
    domain_compatible: bool
    business_definition_compatible: bool
    context_conflict: bool = False
    rationale: str = Field(min_length=1)


class KnowledgeReuseSignals(ContractModel):
    candidates: list[KnowledgeMappingCandidate] = Field(default_factory=list)


class ReusedMapping(ContractModel):
    mapping_id: UUID = Field(default_factory=uuid4)
    field_name: str = Field(min_length=1)
    confidence: Confidence
    priority: int = Field(ge=1)
    search_strategy: Literal[SearchStrategy.SOURCE_HINT_FIRST] = (
        SearchStrategy.SOURCE_HINT_FIRST
    )
    sources: list[SourceAttributeMapping] = Field(min_length=1)
    evidence: list[Evidence] = Field(min_length=1)
    rationale: str = Field(min_length=1)


class RequirementChange(ContractModel):
    action: ChangeAction
    target: str = Field(min_length=1)
    before: str | None = None
    after: str | None = None
    reason: str | None = None


class ChangeSummary(ContractModel):
    changes: list[RequirementChange] = Field(default_factory=list)


class ProcessingTrace(ContractModel):
    prompt_version: str
    model: str
    knowledge_base_queries: list[str] = Field(default_factory=list)
    processing_time_ms: int = Field(ge=0)


class AnalyzeResponse(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    request_id: UUID
    requirement_id: UUID
    revision_id: UUID
    analyzed_requirement: AnalyzedRequirement
    clear_fields: list[ClearFieldSuggestion] = Field(default_factory=list)
    keywords: list[KeywordSuggestion] = Field(default_factory=list)
    reused_mappings: list[ReusedMapping] = Field(default_factory=list)
    change_summary: ChangeSummary | None = None
    warnings: list[str] = Field(default_factory=list)
    trace: ProcessingTrace


class FieldAnalysisSignal(ContractModel):
    name: str = Field(min_length=1)
    normalized_terms: list[str] = Field(default_factory=list)
    requirement_excerpt: str = Field(min_length=1)


class KeywordAnalysisSignal(ContractModel):
    name: str = Field(min_length=1)
    normalized_terms: list[str] = Field(default_factory=list)
    strength: KeywordStrength
    rationale: str = Field(min_length=1)


class RequirementAnalysisSignals(ContractModel):
    analyzed_requirement: AnalyzedRequirement
    clear_fields: list[FieldAnalysisSignal] = Field(default_factory=list)
    keywords: list[KeywordAnalysisSignal] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)


class KnowledgeChunk(ContractModel):
    chunk_id: str | None = None
    text: str = Field(min_length=1)
    similarity_score: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

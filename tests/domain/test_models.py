from uuid import uuid4

import pytest
from pydantic import ValidationError

from analyze_agent.domain.models import (
    AnalyzedRequirement,
    AnalyzeResponse,
    AssetReference,
    AttributeReference,
    Confidence,
    ConfidenceLevel,
    FeedbackDecision,
    FeedbackTargetType,
    InitialAnalysisRequest,
    ProcessingTrace,
    SearchFeedback,
    UpdatedAnalysisRequest,
)


def test_initial_request_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        InitialAnalysisRequest(requirement="Build a GDA.", unknown=True)


def test_field_mapping_feedback_requires_full_mapping() -> None:
    with pytest.raises(ValidationError, match="field_name, asset, and attribute"):
        SearchFeedback(
            candidate_id="candidate-1",
            target_type=FeedbackTargetType.FIELD_MAPPING,
            decision=FeedbackDecision.ACCEPT,
            field_name="Facility_id",
        )


def test_field_mapping_feedback_accepts_asset_and_attribute() -> None:
    feedback = SearchFeedback(
        candidate_id="candidate-1",
        target_type=FeedbackTargetType.FIELD_MAPPING,
        decision=FeedbackDecision.ACCEPT,
        field_name="Facility_id",
        asset=AssetReference(asset_name="facility"),
        attribute=AttributeReference(attribute_name="facility_id"),
    )

    assert feedback.asset is not None
    assert feedback.attribute is not None


def test_updated_request_requires_supplement_or_feedback() -> None:
    with pytest.raises(ValidationError, match="search_feedback is required"):
        UpdatedAnalysisRequest(requirement_id=uuid4())


def test_response_serializes_grouped_contract() -> None:
    response = AnalyzeResponse(
        request_id=uuid4(),
        requirement_id=uuid4(),
        revision_id=uuid4(),
        analyzed_requirement=AnalyzedRequirement(
            summary="Build a regulatory analysis GDA.",
            business_goal="Support ADC review.",
        ),
        trace=ProcessingTrace(
            prompt_version="analyze-requirement-v1",
            model="gemini-test",
            processing_time_ms=12,
        ),
    )

    payload = response.model_dump(mode="json")

    assert payload["schema_version"] == "1.0"
    assert payload["clear_fields"] == []
    assert payload["keywords"] == []
    assert payload["reused_mappings"] == []


def test_confidence_score_is_bounded() -> None:
    with pytest.raises(ValidationError):
        Confidence(level=ConfidenceLevel.HIGH, score=1.1)


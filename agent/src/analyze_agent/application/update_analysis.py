"""Feedback-driven requirement update workflow."""

from __future__ import annotations

from uuid import uuid4

from analyze_agent.application.analysis_pipeline import AnalysisPipeline
from analyze_agent.application.language import validate_english_text
from analyze_agent.domain.confidence import (
    ConfidenceSignals,
    SuggestionKind,
    calculate_confidence,
)
from analyze_agent.domain.models import (
    AnalyzeResponse,
    ChangeAction,
    ChangeSummary,
    Evidence,
    EvidenceType,
    FeedbackDecision,
    FeedbackTargetType,
    RequirementChange,
    ReusedMapping,
    SearchFeedback,
    SourceAttributeMapping,
    UpdatedAnalysisRequest,
)
from analyze_agent.ports.requirement_repository import RequirementRepository
from analyze_agent.ports.requirement_updater import RequirementUpdater
from analyze_agent.workflow_events import (
    StageEventSink,
    WorkflowStage,
    WorkflowTracker,
)


class UpdatedAnalysisService:
    def __init__(
        self,
        *,
        updater: RequirementUpdater,
        pipeline: AnalysisPipeline,
        repository: RequirementRepository,
    ) -> None:
        self._updater = updater
        self._pipeline = pipeline
        self._repository = repository

    async def analyze_update(
        self,
        request: UpdatedAnalysisRequest,
        *,
        event_sink: StageEventSink | None = None,
        job_id: str | None = None,
    ) -> AnalyzeResponse:
        tracker = WorkflowTracker(
            job_id=job_id or str(request.request_id),
            request_id=request.request_id,
            sink=event_sink,
        )
        with tracker.stage(WorkflowStage.VALIDATING_INPUT):
            if request.supplemental_information:
                validate_english_text(
                    request.supplemental_information,
                    field_name="supplemental_information",
                )

        with tracker.stage(WorkflowStage.LOADING_REVISION):
            latest = self._repository.get_latest_revision(request.requirement_id)
        with tracker.stage(WorkflowStage.UPDATING_REQUIREMENT):
            update = await self._updater.update(
                previous_requirement=latest.full_requirement,
                supplemental_information=request.supplemental_information,
                feedback=request.search_feedback,
                previous_output=latest.output_snapshot,
            )
            validate_english_text(
                update.full_requirement,
                field_name="full_requirement",
            )

        changes = [
            *update.changes,
            *[_feedback_change(item) for item in request.search_feedback],
        ]
        revision_id = uuid4()
        response = await self._pipeline.analyze(
            request_id=request.request_id,
            requirement_id=request.requirement_id,
            revision_id=revision_id,
            requirement=update.full_requirement,
            change_summary=ChangeSummary(changes=changes),
            tracker=tracker,
        )
        try:
            _apply_feedback(response, request.search_feedback)
        except Exception as error:
            tracker.fail_once(
                stage=WorkflowStage.CALCULATING_CONFIDENCE,
                error=error,
            )
            raise
        with tracker.stage(WorkflowStage.PERSISTING_REVISION):
            self._repository.append_revision(
                requirement_id=request.requirement_id,
                expected_base_revision_number=latest.revision_number,
                full_requirement=update.full_requirement,
                supplemental_information=request.supplemental_information,
                analyzed_requirement=response.analyzed_requirement.model_dump(
                    mode="json"
                ),
                changes=changes,
                feedback=request.search_feedback,
                output_snapshot=response.model_dump(mode="json"),
            )
        tracker.complete()
        return response


def _apply_feedback(
    response: AnalyzeResponse,
    feedback: list[SearchFeedback],
) -> None:
    rejected = [
        item for item in feedback if item.decision is FeedbackDecision.REJECT
    ]
    accepted_mappings = [
        item
        for item in feedback
        if item.decision is FeedbackDecision.ACCEPT
        and item.target_type is FeedbackTargetType.FIELD_MAPPING
    ]

    response.clear_fields = [
        item
        for item in response.clear_fields
        if not any(_rejects_field(entry, item.name) for entry in rejected)
    ]
    response.reused_mappings = [
        item
        for item in response.reused_mappings
        if not any(_rejects_mapping(entry, item) for entry in rejected)
    ]

    for item in rejected:
        target = _feedback_target(item)
        if target and target.casefold() not in {
            value.casefold()
            for value in response.analyzed_requirement.negative_constraints
        }:
            response.analyzed_requirement.negative_constraints.append(target)

    for item in accepted_mappings:
        mapping = _accepted_mapping(item)
        response.reused_mappings = [
            existing
            for existing in response.reused_mappings
            if existing.field_name.casefold() != mapping.field_name.casefold()
        ]
        response.reused_mappings.append(mapping)

    response.reused_mappings.sort(
        key=lambda item: item.confidence.score,
        reverse=True,
    )
    _assign_priorities(response)


def _accepted_mapping(feedback: SearchFeedback) -> ReusedMapping:
    if (
        feedback.field_name is None
        or feedback.asset is None
        or feedback.attribute is None
    ):
        raise ValueError("Accepted field mapping feedback is incomplete.")
    confidence = calculate_confidence(
        ConfidenceSignals(
            kind=SuggestionKind.MAPPING,
            user_confirmed=True,
        )
    )
    if confidence is None:
        raise RuntimeError("Accepted mapping unexpectedly produced no confidence.")
    return ReusedMapping(
        field_name=feedback.field_name,
        confidence=confidence,
        priority=1,
        sources=[
            SourceAttributeMapping(
                attribute=feedback.attribute,
                asset=feedback.asset,
            )
        ],
        evidence=[
            Evidence(
                type=EvidenceType.USER_FEEDBACK,
                reference=feedback.candidate_id,
                excerpt=feedback.reason,
            )
        ],
        rationale=feedback.reason or "Mapping explicitly accepted by the user.",
    )


def _assign_priorities(response: AnalyzeResponse) -> None:
    next_priority = 1
    for mapping in response.reused_mappings:
        mapping.priority = next_priority
        next_priority += 1
    for field in response.clear_fields:
        field.priority = next_priority
        next_priority += 1
    for keyword in response.keywords:
        keyword.priority = next_priority
        next_priority += 1


def _rejects_field(feedback: SearchFeedback, field_name: str) -> bool:
    return (
        feedback.target_type is FeedbackTargetType.FIELD_MAPPING
        and feedback.field_name is not None
        and feedback.field_name.casefold() == field_name.casefold()
    )


def _rejects_mapping(
    feedback: SearchFeedback,
    mapping: ReusedMapping,
) -> bool:
    if feedback.target_type is FeedbackTargetType.FIELD_MAPPING:
        return (
            feedback.field_name is not None
            and feedback.field_name.casefold() == mapping.field_name.casefold()
        )
    if feedback.target_type is FeedbackTargetType.ASSET and feedback.asset:
        return any(
            _same_asset(feedback.asset, source.asset) for source in mapping.sources
        )
    if feedback.target_type is FeedbackTargetType.ATTRIBUTE and feedback.attribute:
        return any(
            _same_attribute(feedback.attribute, source.attribute)
            for source in mapping.sources
        )
    return False


def _same_asset(left, right) -> bool:
    return _same_optional(left.asset_id, right.asset_id) or _same_optional(
        left.asset_name, right.asset_name
    )


def _same_attribute(left, right) -> bool:
    return _same_optional(
        left.attribute_id, right.attribute_id
    ) or _same_optional(left.attribute_name, right.attribute_name)


def _same_optional(left: str | None, right: str | None) -> bool:
    return bool(left and right and left.casefold() == right.casefold())


def _feedback_change(feedback: SearchFeedback) -> RequirementChange:
    action = (
        ChangeAction.CONFIRM
        if feedback.decision is FeedbackDecision.ACCEPT
        else ChangeAction.REJECT
    )
    return RequirementChange(
        action=action,
        target=_feedback_target(feedback) or feedback.candidate_id,
        reason=feedback.reason,
    )


def _feedback_target(feedback: SearchFeedback) -> str | None:
    if feedback.target_type is FeedbackTargetType.FIELD_MAPPING:
        return feedback.field_name
    if feedback.target_type is FeedbackTargetType.ASSET and feedback.asset:
        return feedback.asset.asset_id or feedback.asset.asset_name
    if feedback.target_type is FeedbackTargetType.ATTRIBUTE and feedback.attribute:
        return feedback.attribute.attribute_id or feedback.attribute.attribute_name
    return None

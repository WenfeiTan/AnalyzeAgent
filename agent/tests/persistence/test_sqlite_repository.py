from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest

from analyze_agent.domain.models import (
    AssetReference,
    AttributeReference,
    ChangeAction,
    FeedbackDecision,
    FeedbackTargetType,
    RequirementChange,
    SearchFeedback,
)
from analyze_agent.persistence.errors import (
    RequirementNotFoundError,
    RevisionConflictError,
)
from analyze_agent.persistence.sqlite_repository import SQLiteRequirementRepository


@pytest.fixture
def repository(tmp_path) -> SQLiteRequirementRepository:
    result = SQLiteRequirementRepository(tmp_path / "analyze-agent.sqlite3")
    result.initialize()
    return result


def test_create_and_restore_initial_revision(
    repository: SQLiteRequirementRepository,
) -> None:
    revision = repository.create_requirement(
        full_requirement="Build a GDA for ADC review.",
        analyzed_requirement={"summary": "ADC review GDA"},
        output_snapshot={"clear_fields": [], "keywords": ["ADC"]},
    )

    restored = repository.get_latest_revision(revision.requirement_id)

    assert restored == revision
    assert restored.revision_number == 1
    assert restored.output_snapshot == {
        "clear_fields": [],
        "keywords": ["ADC"],
    }
    summaries = repository.list_requirements()
    assert summaries[0].requirement_id == revision.requirement_id
    assert summaries[0].latest_revision_number == 1
    assert summaries[0].summary == revision.full_requirement


def test_append_revision_preserves_history_and_feedback(
    repository: SQLiteRequirementRepository,
) -> None:
    initial = repository.create_requirement(
        full_requirement="Build an ADC review GDA."
    )
    feedback = SearchFeedback(
        candidate_id="candidate-1",
        target_type=FeedbackTargetType.FIELD_MAPPING,
        decision=FeedbackDecision.ACCEPT,
        field_name="ADC_entity_country",
        asset=AssetReference(asset_name="adc_entity"),
        attribute=AttributeReference(attribute_name="entity_country"),
    )
    change = RequirementChange(
        action=ChangeAction.ADD,
        target="ADC_entity_country",
        after="Include ADC entity country.",
    )

    updated = repository.append_revision(
        requirement_id=initial.requirement_id,
        expected_base_revision_number=1,
        full_requirement=(
            "Build an ADC review GDA including the ADC entity country."
        ),
        supplemental_information="Include the ADC entity country.",
        changes=[change],
        feedback=[feedback],
    )

    history = repository.list_revisions(initial.requirement_id)

    assert [item.revision_number for item in history] == [1, 2]
    assert history[0].full_requirement == "Build an ADC review GDA."
    assert updated.feedback == [feedback]
    assert updated.changes == [change]


def test_stale_revision_is_rejected(
    repository: SQLiteRequirementRepository,
) -> None:
    initial = repository.create_requirement(full_requirement="Build a GDA.")
    repository.append_revision(
        requirement_id=initial.requirement_id,
        expected_base_revision_number=1,
        full_requirement="Build a Basel GDA.",
        supplemental_information="Add Basel.",
    )

    with pytest.raises(RevisionConflictError) as error:
        repository.append_revision(
            requirement_id=initial.requirement_id,
            expected_base_revision_number=1,
            full_requirement="Build an ADC GDA.",
            supplemental_information="Add ADC.",
        )

    assert error.value.actual_revision_number == 2


def test_unknown_requirement_is_rejected(
    repository: SQLiteRequirementRepository,
) -> None:
    with pytest.raises(RequirementNotFoundError):
        repository.get_latest_revision(uuid4())


def test_concurrent_updates_do_not_overwrite_each_other(
    repository: SQLiteRequirementRepository,
) -> None:
    initial = repository.create_requirement(full_requirement="Build a GDA.")
    barrier = Barrier(2)

    def append(suffix: str) -> str:
        barrier.wait()
        try:
            repository.append_revision(
                requirement_id=initial.requirement_id,
                expected_base_revision_number=1,
                full_requirement=f"Build a {suffix} GDA.",
                supplemental_information=f"Add {suffix}.",
            )
        except RevisionConflictError:
            return "conflict"
        return "created"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(append, ["Basel", "ADC"]))

    assert sorted(results) == ["conflict", "created"]
    assert len(repository.list_revisions(initial.requirement_id)) == 2

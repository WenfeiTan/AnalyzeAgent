import pytest
from pydantic import ValidationError

from analyze_agent.domain.confidence import (
    ConfidenceSignals,
    SuggestionKind,
    calculate_confidence,
)
from analyze_agent.domain.models import ConfidenceLevel


@pytest.mark.parametrize(
    ("signals", "score", "level"),
    [
        (
            ConfidenceSignals(
                kind=SuggestionKind.MAPPING,
                verified_success_case=True,
            ),
            0.9,
            ConfidenceLevel.HIGH,
        ),
        (
            ConfidenceSignals(
                kind=SuggestionKind.FIELD,
                explicit_requirement=True,
            ),
            0.7,
            ConfidenceLevel.MEDIUM,
        ),
        (
            ConfidenceSignals(
                kind=SuggestionKind.KEYWORD,
                core_keyword=True,
            ),
            0.6,
            ConfidenceLevel.MEDIUM,
        ),
        (
            ConfidenceSignals(
                kind=SuggestionKind.KEYWORD,
                inferred_keyword=True,
            ),
            0.4,
            ConfidenceLevel.LOW,
        ),
    ],
)
def test_confidence_baselines(
    signals: ConfidenceSignals,
    score: float,
    level: ConfidenceLevel,
) -> None:
    confidence = calculate_confidence(signals)

    assert confidence is not None
    assert confidence.score == score
    assert confidence.level is level


def test_user_confirmation_and_penalties_are_deterministic() -> None:
    confidence = calculate_confidence(
        ConfidenceSignals(
            kind=SuggestionKind.FIELD,
            explicit_requirement=True,
            user_confirmed=True,
            ambiguous=True,
        )
    )

    assert confidence is not None
    assert confidence.score == 0.7
    assert confidence.level is ConfidenceLevel.MEDIUM


def test_user_rejection_excludes_candidate() -> None:
    confidence = calculate_confidence(
        ConfidenceSignals(
            kind=SuggestionKind.KEYWORD,
            core_keyword=True,
            user_rejected=True,
        )
    )

    assert confidence is None


def test_mapping_requires_verified_evidence() -> None:
    with pytest.raises(ValidationError, match="verified success case"):
        ConfidenceSignals(kind=SuggestionKind.MAPPING)


def test_keyword_requires_exactly_one_strength() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        ConfidenceSignals(kind=SuggestionKind.KEYWORD)


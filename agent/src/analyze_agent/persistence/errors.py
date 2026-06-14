"""Persistence-specific exceptions."""

from uuid import UUID


class RequirementRepositoryError(RuntimeError):
    """Base repository failure."""


class RequirementNotFoundError(RequirementRepositoryError):
    def __init__(self, requirement_id: UUID) -> None:
        super().__init__(f"Requirement {requirement_id} was not found.")
        self.requirement_id = requirement_id


class RevisionConflictError(RequirementRepositoryError):
    def __init__(
        self,
        *,
        requirement_id: UUID,
        expected_revision_number: int,
        actual_revision_number: int,
    ) -> None:
        super().__init__(
            f"Requirement {requirement_id} changed from revision "
            f"{expected_revision_number} to {actual_revision_number}."
        )
        self.requirement_id = requirement_id
        self.expected_revision_number = expected_revision_number
        self.actual_revision_number = actual_revision_number


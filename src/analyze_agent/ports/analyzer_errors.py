"""Failures exposed by requirement analyzer adapters."""


class RequirementAnalysisError(RuntimeError):
    """The model failed to produce valid structured requirement analysis."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


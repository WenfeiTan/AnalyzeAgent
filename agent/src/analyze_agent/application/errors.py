"""Application-level input and workflow failures."""


class UnsupportedRequirementLanguage(ValueError):
    """Raised when a v1 request contains unsupported non-English text."""


class AnalysisWorkflowError(RuntimeError):
    """Raised when an analysis workflow cannot produce a valid result."""


"""Failures exposed by Knowledge Base reconstruction adapters."""


class KnowledgeReconstructionError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


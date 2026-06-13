"""Transport-independent Knowledge Base retrieval failures."""


class KnowledgeRetrievalError(RuntimeError):
    """Base failure exposed by Knowledge Base retriever adapters."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class KnowledgeRetrievalTimeout(KnowledgeRetrievalError):
    def __init__(self, message: str = "Knowledge Base retrieval timed out.") -> None:
        super().__init__(message, retryable=True)


class InvalidKnowledgeResponse(KnowledgeRetrievalError):
    def __init__(self, message: str = "Knowledge Base returned an invalid response.") -> None:
        super().__init__(message, retryable=False)


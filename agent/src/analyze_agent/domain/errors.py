"""Typed error contracts shared by application adapters."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "validation_error"
    CONFIGURATION_ERROR = "configuration_error"
    REQUIREMENT_NOT_FOUND = "requirement_not_found"
    REVISION_CONFLICT = "revision_conflict"
    MODEL_ERROR = "model_error"
    RETRIEVER_ERROR = "retriever_error"
    PROCESSING_ERROR = "processing_error"


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str = Field(min_length=1)
    retryable: bool = False
    context: dict[str, Any] = Field(default_factory=dict)


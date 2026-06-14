"""Typed, request-scoped workflow events for progress consumers."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from enum import StrEnum
from time import perf_counter
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStage(StrEnum):
    VALIDATING_INPUT = "validating_input"
    LOADING_REVISION = "loading_revision"
    UPDATING_REQUIREMENT = "updating_requirement"
    ANALYZING_REQUIREMENT = "analyzing_requirement"
    SEARCHING_KNOWLEDGE_BASE = "searching_knowledge_base"
    RECONSTRUCTING_MAPPINGS = "reconstructing_mappings"
    CALCULATING_CONFIDENCE = "calculating_confidence"
    PERSISTING_REVISION = "persisting_revision"
    COMPLETED = "completed"
    FAILED = "failed"


class StageStatus(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class StageEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    job_id: str = Field(min_length=1)
    request_id: UUID
    stage: WorkflowStage
    status: StageStatus
    sequence: int = Field(ge=1)
    timestamp: datetime
    duration_ms: float | None = Field(default=None, ge=0)
    metadata: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict
    )


class StageEventSink(Protocol):
    def emit(self, event: StageEvent) -> None:
        """Consume an immutable workflow event without blocking the workflow."""


class NullStageEventSink:
    def emit(self, event: StageEvent) -> None:
        del event


class MemoryStageEventSink:
    """Small in-memory sink for tests and local embedding."""

    def __init__(self) -> None:
        self.events: list[StageEvent] = []

    def emit(self, event: StageEvent) -> None:
        self.events.append(event)


class WorkflowTracker:
    """Emit ordered stage events for one workflow invocation."""

    def __init__(
        self,
        *,
        job_id: str,
        request_id: UUID,
        sink: StageEventSink | None = None,
    ) -> None:
        self._job_id = job_id
        self._request_id = request_id
        self._sink = sink or NullStageEventSink()
        self._sequence = 0
        self._terminal = False

    @contextmanager
    def stage(self, stage: WorkflowStage) -> Iterator[None]:
        started_at = perf_counter()
        self._publish(stage=stage, status=StageStatus.STARTED)
        try:
            yield
        except Exception as error:
            self.fail_once(stage=stage, error=error)
            raise
        self._publish(
            stage=stage,
            status=StageStatus.COMPLETED,
            duration_ms=(perf_counter() - started_at) * 1000,
        )

    def complete(self) -> None:
        if self._terminal:
            return
        self._terminal = True
        self._publish(
            stage=WorkflowStage.COMPLETED,
            status=StageStatus.COMPLETED,
        )

    def fail_once(self, *, stage: WorkflowStage, error: Exception) -> None:
        if self._terminal:
            return
        self._terminal = True
        self._publish(
            stage=WorkflowStage.FAILED,
            status=StageStatus.FAILED,
            metadata={
                "failed_stage": stage.value,
                "exception_type": type(error).__name__,
            },
        )

    def _publish(
        self,
        *,
        stage: WorkflowStage,
        status: StageStatus,
        duration_ms: float | None = None,
        metadata: Mapping[str, str | int | float | bool | None] | None = None,
    ) -> None:
        self._sequence += 1
        self._sink.emit(
            StageEvent(
                job_id=self._job_id,
                request_id=self._request_id,
                stage=stage,
                status=status,
                sequence=self._sequence,
                timestamp=datetime.now(UTC),
                duration_ms=(
                    None if duration_ms is None else round(duration_ms, 3)
                ),
                metadata=dict(metadata or {}),
            )
        )

"""Deterministic Knowledge Base retriever used before vector-mcp integration."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from analyze_agent.domain.models import KnowledgeChunk
from analyze_agent.ports.retriever_errors import (
    InvalidKnowledgeResponse,
    KnowledgeRetrievalError,
    KnowledgeRetrievalTimeout,
)

_CHUNKS_ADAPTER = TypeAdapter(list[KnowledgeChunk])


@dataclass(frozen=True, slots=True)
class FakeRetrievalScenario:
    chunks: tuple[KnowledgeChunk, ...] = ()
    error: KnowledgeRetrievalError | None = None
    delay_seconds: float = 0.0


class FakeKnowledgeBaseRetriever:
    """Return configured chunks or failures while recording all query text."""

    def __init__(
        self,
        scenarios: dict[str, FakeRetrievalScenario] | None = None,
        *,
        default_scenario: FakeRetrievalScenario | None = None,
    ) -> None:
        self._scenarios = dict(scenarios or {})
        self._default_scenario = default_scenario or FakeRetrievalScenario()
        self.queries: list[str] = []

    async def search(self, text: str) -> list[KnowledgeChunk]:
        self.queries.append(text)
        scenario = self._scenarios.get(text, self._default_scenario)
        if scenario.delay_seconds:
            await asyncio.sleep(scenario.delay_seconds)
        if scenario.error is not None:
            raise scenario.error
        return list(scenario.chunks)


def load_fake_scenario(path: str | Path) -> FakeRetrievalScenario:
    """Load a test scenario without assuming the real MCP payload shape."""

    try:
        raw_payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InvalidKnowledgeResponse(
            f"Unable to load fake retrieval payload: {error}"
        ) from error
    return parse_fake_scenario(raw_payload)


def parse_fake_scenario(raw_payload: object) -> FakeRetrievalScenario:
    """Validate a decoded Fake Knowledge Base payload."""
    if not isinstance(raw_payload, dict):
        raise InvalidKnowledgeResponse("Fake retrieval payload must be an object.")

    error_name = raw_payload.get("error")
    if error_name == "timeout":
        return FakeRetrievalScenario(error=KnowledgeRetrievalTimeout())
    if error_name is not None:
        return FakeRetrievalScenario(
            error=InvalidKnowledgeResponse(str(raw_payload.get("message") or error_name))
        )

    try:
        chunks = _CHUNKS_ADAPTER.validate_python(raw_payload.get("chunks", []))
    except ValidationError as error:
        raise InvalidKnowledgeResponse(
            f"Fake retrieval chunks failed validation: {error}"
        ) from error

    delay_seconds = raw_payload.get("delay_seconds", 0.0)
    if not isinstance(delay_seconds, int | float) or delay_seconds < 0:
        raise InvalidKnowledgeResponse(
            "Fake retrieval delay_seconds must be a non-negative number."
        )
    return FakeRetrievalScenario(
        chunks=tuple(chunks),
        delay_seconds=float(delay_seconds),
    )

"""Gemini adapter for reconstructing candidate mappings from chunks."""

from __future__ import annotations

import json
from typing import Any

from google import genai

from analyze_agent.adapters.gemini_structured import (
    StructuredOutputError,
    generate_structured,
)
from analyze_agent.domain.models import (
    AnalyzedRequirement,
    KnowledgeChunk,
    KnowledgeReuseSignals,
)
from analyze_agent.ports.reconstructor_errors import KnowledgeReconstructionError

RECONSTRUCT_KNOWLEDGE_PROMPT_VERSION = "reconstruct-knowledge-v1"

_SYSTEM_INSTRUCTION = """
You reconstruct candidate Asset Discovery mappings from untrusted Knowledge Base chunks.

Return only the requested structured schema.
- Use only facts explicitly present in the supplied chunks.
- Never invent a field, attribute, asset, source system, chunk ID, or success status.
- A mapping source must include both an attribute identity and an asset identity.
- supporting_chunk_ids must contain only IDs supplied in the input.
- Mark compatibility booleans conservatively and record conflicts.
- Incomplete evidence must remain incomplete; do not fill gaps from general knowledge.
""".strip()


class GeminiKnowledgeReconstructor:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        client: Any | None = None,
        repair_attempts: int = 1,
    ) -> None:
        self.model = model
        self._client = client or genai.Client(api_key=api_key)
        self._repair_attempts = repair_attempts

    async def reconstruct(
        self,
        *,
        requirement: str,
        analyzed_requirement: AnalyzedRequirement,
        chunks: list[KnowledgeChunk],
    ) -> KnowledgeReuseSignals:
        contents = json.dumps(
            {
                "requirement": requirement,
                "analyzed_requirement": analyzed_requirement.model_dump(mode="json"),
                "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
            },
            ensure_ascii=True,
        )
        try:
            return await generate_structured(
                client=self._client,
                model=self.model,
                contents=contents,
                system_instruction=_SYSTEM_INSTRUCTION,
                schema=KnowledgeReuseSignals,
                repair_attempts=self._repair_attempts,
            )
        except StructuredOutputError as error:
            raise KnowledgeReconstructionError(
                f"Gemini returned invalid knowledge reconstruction: {error}",
                retryable=False,
            ) from error
        except Exception as error:
            raise KnowledgeReconstructionError(
                f"Gemini knowledge reconstruction failed: {error}",
                retryable=True,
            ) from error

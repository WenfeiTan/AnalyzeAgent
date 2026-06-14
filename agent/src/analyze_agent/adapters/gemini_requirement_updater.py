"""Gemini adapter for producing a complete updated requirement."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from google import genai

from analyze_agent.adapters.gemini_structured import (
    StructuredOutputError,
    generate_structured,
)
from analyze_agent.domain.models import RequirementUpdateSignals, SearchFeedback
from analyze_agent.ports.analyzer_errors import RequirementAnalysisError

UPDATE_REQUIREMENT_PROMPT_VERSION = "update-requirement-v1"

_SYSTEM_INSTRUCTION = """
You update an existing English Asset Discovery requirement.

Return only the requested structured schema.
- Produce a complete standalone English requirement, not an incremental note.
- Apply supplemental corrections, additions, and removals.
- Apply accept/reject feedback to asset, attribute, and field mappings.
- Preserve valid prior intent unless the new information changes it.
- Record a concise structured change list.
- Do not create revision IDs, confidence, priorities, assets, or attributes that
  were not present in the supplied requirement, feedback, or prior output.
""".strip()


class GeminiRequirementUpdater:
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

    async def update(
        self,
        *,
        previous_requirement: str,
        supplemental_information: str | None,
        feedback: list[SearchFeedback],
        previous_output: Mapping[str, Any] | None,
    ) -> RequirementUpdateSignals:
        contents = json.dumps(
            {
                "previous_requirement": previous_requirement,
                "supplemental_information": supplemental_information,
                "feedback": [
                    item.model_dump(mode="json") for item in feedback
                ],
                "previous_output": previous_output,
            },
            ensure_ascii=True,
            default=str,
        )
        try:
            return await generate_structured(
                client=self._client,
                model=self.model,
                contents=contents,
                system_instruction=_SYSTEM_INSTRUCTION,
                schema=RequirementUpdateSignals,
                repair_attempts=self._repair_attempts,
            )
        except StructuredOutputError as error:
            raise RequirementAnalysisError(
                f"Gemini returned an invalid updated requirement: {error}",
                retryable=False,
            ) from error
        except Exception as error:
            raise RequirementAnalysisError(
                f"Gemini requirement update failed: {error}",
                retryable=True,
            ) from error

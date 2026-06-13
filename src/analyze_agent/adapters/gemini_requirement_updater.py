"""Gemini adapter for producing a complete updated requirement."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

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
    ) -> None:
        self.model = model
        self._client = client or genai.Client(api_key=api_key)

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
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_INSTRUCTION,
                    temperature=0,
                    response_mime_type="application/json",
                    response_schema=RequirementUpdateSignals,
                ),
            )
            if isinstance(response.parsed, RequirementUpdateSignals):
                return response.parsed
            if response.parsed is not None:
                return RequirementUpdateSignals.model_validate(response.parsed)
            if response.text:
                return RequirementUpdateSignals.model_validate_json(response.text)
        except (ValidationError, ValueError, TypeError) as error:
            raise RequirementAnalysisError(
                f"Gemini returned an invalid updated requirement: {error}",
                retryable=False,
            ) from error
        except Exception as error:
            raise RequirementAnalysisError(
                f"Gemini requirement update failed: {error}",
                retryable=True,
            ) from error

        raise RequirementAnalysisError(
            "Gemini returned no structured updated requirement.",
            retryable=False,
        )


"""Gemini adapter for strict structured requirement analysis."""

from __future__ import annotations

from typing import Any

from google import genai

from analyze_agent.adapters.gemini_structured import (
    StructuredOutputError,
    generate_structured,
)
from analyze_agent.domain.models import RequirementAnalysisSignals
from analyze_agent.ports.analyzer_errors import RequirementAnalysisError

ANALYZE_REQUIREMENT_PROMPT_VERSION = "analyze-requirement-v1"

_SYSTEM_INSTRUCTION = """
You analyze English Asset Discovery requirements.

Return only the requested structured schema.
- Preserve the user's business intent without inventing facts.
- A clear field is a field name explicitly present in the requirement.
- A keyword is a business, regulatory, or domain concept useful for search.
- Do not invent source assets, source attributes, mappings, IDs, confidence,
  priorities, or revision information.
- Keep acronyms as written unless the requirement explicitly expands them.
- Record ambiguity instead of guessing.
""".strip()


class GeminiRequirementAnalyzer:
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

    async def analyze(self, requirement: str) -> RequirementAnalysisSignals:
        try:
            return await generate_structured(
                client=self._client,
                model=self.model,
                contents=requirement,
                system_instruction=_SYSTEM_INSTRUCTION,
                schema=RequirementAnalysisSignals,
                repair_attempts=self._repair_attempts,
            )
        except StructuredOutputError as error:
            raise RequirementAnalysisError(
                f"Gemini returned invalid requirement analysis: {error}",
                retryable=False,
            ) from error
        except Exception as error:
            raise RequirementAnalysisError(
                f"Gemini requirement analysis failed: {error}",
                retryable=True,
            ) from error

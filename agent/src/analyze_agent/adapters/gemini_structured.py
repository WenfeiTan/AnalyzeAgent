"""Bounded structured-output generation shared by Gemini adapters."""

from __future__ import annotations

from typing import Any, TypeVar

from google.genai import types
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(ValueError):
    """Gemini returned empty or schema-invalid structured output."""


async def generate_structured(
    *,
    client: Any,
    model: str,
    contents: str,
    system_instruction: str,
    schema: type[T],
    repair_attempts: int,
) -> T:
    current_contents = contents
    last_error: BaseException | None = None

    for attempt in range(repair_attempts + 1):
        response = await client.aio.models.generate_content(
            model=model,
            contents=current_contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0,
                response_mime_type="application/json",
                response_json_schema=schema.model_json_schema(),
            ),
        )
        try:
            parsed = getattr(response, "parsed", None)
            if isinstance(parsed, schema):
                return parsed
            if parsed is not None:
                return schema.model_validate(parsed)
            text = getattr(response, "text", None)
            if text:
                return schema.model_validate_json(text)
            raise StructuredOutputError("Gemini returned no structured output.")
        except (ValidationError, ValueError, TypeError) as error:
            last_error = error
            if attempt >= repair_attempts:
                break
            current_contents = (
                f"{contents}\n\n"
                "The previous response did not match the required schema. "
                "Return only valid JSON matching the schema."
            )

    raise StructuredOutputError(
        f"Gemini structured output failed after {repair_attempts + 1} attempt(s): "
        f"{last_error}"
    ) from last_error

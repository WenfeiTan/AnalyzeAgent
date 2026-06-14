"""Deterministic language boundary checks for v1 English requirements."""

from __future__ import annotations

import re

from analyze_agent.application.errors import UnsupportedRequirementLanguage

_ASCII_LETTER = re.compile(r"[A-Za-z]")


def validate_english_text(text: str, *, field_name: str) -> None:
    if not _ASCII_LETTER.search(text):
        raise UnsupportedRequirementLanguage(
            f"{field_name} must contain English text."
        )
    if any(_is_cjk(character) for character in text):
        raise UnsupportedRequirementLanguage(
            f"{field_name} must be English in Analyze Agent v1."
        )


def _is_cjk(character: str) -> bool:
    codepoint = ord(character)
    return (
        0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
    )


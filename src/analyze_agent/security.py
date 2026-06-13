"""Lightweight detection of instruction-like content in untrusted text."""

from __future__ import annotations

import re

_INJECTION_PATTERNS = (
    re.compile(r"\bignore (?:all |the )?(?:previous|prior) instructions?\b", re.I),
    re.compile(r"\bsystem prompt\b", re.I),
    re.compile(r"<\s*/?\s*system\s*>", re.I),
    re.compile(r"\b(?:call|invoke|execute) (?:the )?(?:tool|function)\b", re.I),
)


def has_prompt_injection_pattern(text: str) -> bool:
    return any(pattern.search(text) for pattern in _INJECTION_PATTERNS)


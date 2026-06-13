"""Environment-backed runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_LOG_LEVEL = "INFO"
VALID_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    google_api_key: str | None
    model: str
    log_level: str


def load_settings(*, require_api_key: bool) -> Settings:
    api_key = _optional_value("GOOGLE_API_KEY")
    model = _optional_value("ANALYZE_AGENT_MODEL") or DEFAULT_MODEL
    log_level = (_optional_value("ANALYZE_AGENT_LOG_LEVEL") or DEFAULT_LOG_LEVEL).upper()

    if require_api_key and not api_key:
        raise ConfigurationError(
            "GOOGLE_API_KEY is required to run Analyze Agent. "
            "Set it in the environment; see .env.example."
        )
    if log_level not in VALID_LOG_LEVELS:
        allowed = ", ".join(sorted(VALID_LOG_LEVELS))
        raise ConfigurationError(
            f"ANALYZE_AGENT_LOG_LEVEL must be one of: {allowed}."
        )

    return Settings(google_api_key=api_key, model=model, log_level=log_level)


def _optional_value(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def main() -> None:
    settings = load_settings(require_api_key=True)
    print(
        "Configuration OK: "
        f"model={settings.model}, log_level={settings.log_level}, api_key=set"
    )


if __name__ == "__main__":
    main()


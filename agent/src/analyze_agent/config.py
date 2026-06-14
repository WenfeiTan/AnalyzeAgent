"""Environment-backed runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_DATABASE_PATH = Path("data/analyze-agent.sqlite3")
VALID_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    google_api_key: str | None
    model: str
    log_level: str
    database_path: Path
    model_timeout_seconds: float = 30.0
    retriever_timeout_seconds: float = 10.0
    max_attempts: int = 2
    schema_repair_attempts: int = 1


def load_settings(*, require_api_key: bool) -> Settings:
    api_key = _optional_value("GOOGLE_API_KEY")
    model = _optional_value("ANALYZE_AGENT_MODEL") or DEFAULT_MODEL
    log_level = (_optional_value("ANALYZE_AGENT_LOG_LEVEL") or DEFAULT_LOG_LEVEL).upper()
    database_path = Path(
        _optional_value("ANALYZE_AGENT_DATABASE_PATH") or DEFAULT_DATABASE_PATH
    )
    model_timeout_seconds = _positive_float(
        "ANALYZE_AGENT_MODEL_TIMEOUT_SECONDS", default=30.0
    )
    retriever_timeout_seconds = _positive_float(
        "ANALYZE_AGENT_RETRIEVER_TIMEOUT_SECONDS", default=10.0
    )
    max_attempts = _positive_int("ANALYZE_AGENT_MAX_ATTEMPTS", default=2)
    schema_repair_attempts = _nonnegative_int(
        "ANALYZE_AGENT_SCHEMA_REPAIR_ATTEMPTS", default=1
    )

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

    return Settings(
        google_api_key=api_key,
        model=model,
        log_level=log_level,
        database_path=database_path,
        model_timeout_seconds=model_timeout_seconds,
        retriever_timeout_seconds=retriever_timeout_seconds,
        max_attempts=max_attempts,
        schema_repair_attempts=schema_repair_attempts,
    )


def _optional_value(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _positive_float(name: str, *, default: float) -> float:
    value = _optional_value(name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be a number.") from error
    if parsed <= 0:
        raise ConfigurationError(f"{name} must be greater than zero.")
    return parsed


def _positive_int(name: str, *, default: int) -> int:
    value = _nonnegative_int(name, default=default)
    if value == 0:
        raise ConfigurationError(f"{name} must be greater than zero.")
    return value


def _nonnegative_int(name: str, *, default: int) -> int:
    value = _optional_value(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an integer.") from error
    if parsed < 0:
        raise ConfigurationError(f"{name} must not be negative.")
    return parsed


def main() -> None:
    settings = load_settings(require_api_key=True)
    print(
        "Configuration OK: "
        f"model={settings.model}, log_level={settings.log_level}, "
        f"database_path={settings.database_path}, api_key=set"
    )


if __name__ == "__main__":
    main()

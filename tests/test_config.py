import pytest

from analyze_agent.config import (
    DEFAULT_DATABASE_PATH,
    DEFAULT_MODEL,
    ConfigurationError,
    load_settings,
)


def test_settings_use_safe_defaults_without_runtime_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("ANALYZE_AGENT_MODEL", raising=False)
    monkeypatch.delenv("ANALYZE_AGENT_LOG_LEVEL", raising=False)
    monkeypatch.delenv("ANALYZE_AGENT_DATABASE_PATH", raising=False)

    settings = load_settings(require_api_key=False)

    assert settings.google_api_key is None
    assert settings.model == DEFAULT_MODEL
    assert settings.log_level == "INFO"
    assert settings.database_path == DEFAULT_DATABASE_PATH


def test_runtime_settings_require_gemini_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(ConfigurationError, match="GOOGLE_API_KEY is required"):
        load_settings(require_api_key=True)


def test_invalid_log_level_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANALYZE_AGENT_LOG_LEVEL", "verbose")

    with pytest.raises(ConfigurationError, match="ANALYZE_AGENT_LOG_LEVEL"):
        load_settings(require_api_key=False)

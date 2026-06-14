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
    monkeypatch.delenv("ANALYZE_AGENT_MODEL_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("ANALYZE_AGENT_RETRIEVER_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("ANALYZE_AGENT_MAX_ATTEMPTS", raising=False)
    monkeypatch.delenv("ANALYZE_AGENT_SCHEMA_REPAIR_ATTEMPTS", raising=False)

    settings = load_settings(require_api_key=False)

    assert settings.google_api_key is None
    assert settings.model == DEFAULT_MODEL
    assert settings.log_level == "INFO"
    assert settings.database_path == DEFAULT_DATABASE_PATH
    assert settings.model_timeout_seconds == 30.0
    assert settings.retriever_timeout_seconds == 10.0
    assert settings.max_attempts == 2
    assert settings.schema_repair_attempts == 1


def test_runtime_settings_require_gemini_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(ConfigurationError, match="GOOGLE_API_KEY is required"):
        load_settings(require_api_key=True)


@pytest.mark.parametrize(
    "api_key",
    [
        '"test-key"',
        "'test-key'",
        "\u201ctest-key\u201d",
        "\u2018test-key\u2019",
    ],
)
def test_api_key_rejects_surrounding_quotes(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str,
) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", api_key)

    with pytest.raises(ConfigurationError, match="quote characters"):
        load_settings(require_api_key=False)


def test_invalid_log_level_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANALYZE_AGENT_LOG_LEVEL", "verbose")

    with pytest.raises(ConfigurationError, match="ANALYZE_AGENT_LOG_LEVEL"):
        load_settings(require_api_key=False)


def test_invalid_retry_configuration_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANALYZE_AGENT_MAX_ATTEMPTS", "0")

    with pytest.raises(ConfigurationError, match="greater than zero"):
        load_settings(require_api_key=False)

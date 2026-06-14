import asyncio
from types import SimpleNamespace

import pytest

from analyze_agent.adapters.gemini_requirement_analyzer import (
    GeminiRequirementAnalyzer,
)
from analyze_agent.domain.models import (
    AnalyzedRequirement,
    RequirementAnalysisSignals,
)
from analyze_agent.ports.analyzer_errors import RequirementAnalysisError


class StubModels:
    def __init__(self, response) -> None:
        self.responses = (
            list(response) if isinstance(response, list) else [response]
        )
        self.calls = []

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.responses) == 1:
            return self.responses[0]
        return self.responses.pop(0)


def _client(response):
    models = StubModels(response)
    return SimpleNamespace(aio=SimpleNamespace(models=models)), models


def test_gemini_adapter_returns_typed_parsed_response() -> None:
    signals = RequirementAnalysisSignals(
        analyzed_requirement=AnalyzedRequirement(
            summary="Build an ADC review GDA.",
            business_goal="Support ADC review.",
        )
    )
    client, models = _client(SimpleNamespace(parsed=signals, text=None))
    analyzer = GeminiRequirementAnalyzer(
        api_key="test",
        model="gemini-test",
        client=client,
    )

    result = asyncio.run(analyzer.analyze("Build an ADC review GDA."))

    assert result == signals
    assert models.calls[0]["model"] == "gemini-test"
    config = models.calls[0]["config"]
    assert config.response_schema is None
    assert config.response_json_schema == RequirementAnalysisSignals.model_json_schema()


def test_gemini_adapter_rejects_empty_response() -> None:
    client, _ = _client(SimpleNamespace(parsed=None, text=None))
    analyzer = GeminiRequirementAnalyzer(
        api_key="test",
        model="gemini-test",
        client=client,
    )

    with pytest.raises(RequirementAnalysisError, match="no structured"):
        asyncio.run(analyzer.analyze("Build an ADC review GDA."))


def test_gemini_adapter_repairs_schema_once() -> None:
    signals = RequirementAnalysisSignals(
        analyzed_requirement=AnalyzedRequirement(
            summary="Build an ADC review GDA.",
            business_goal="Support ADC review.",
        )
    )
    client, models = _client(
        [
            SimpleNamespace(parsed=None, text="{not-json"),
            SimpleNamespace(parsed=signals, text=None),
        ]
    )
    analyzer = GeminiRequirementAnalyzer(
        api_key="test",
        model="gemini-test",
        client=client,
        repair_attempts=1,
    )

    result = asyncio.run(analyzer.analyze("Build an ADC review GDA."))

    assert result == signals
    assert len(models.calls) == 2

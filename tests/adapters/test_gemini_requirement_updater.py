import asyncio
from types import SimpleNamespace

from analyze_agent.adapters.gemini_requirement_updater import (
    GeminiRequirementUpdater,
)
from analyze_agent.domain.models import RequirementUpdateSignals


class StubModels:
    def __init__(self, response) -> None:
        self.response = response

    async def generate_content(self, **kwargs):
        return self.response


def test_gemini_updater_returns_complete_typed_requirement() -> None:
    signals = RequirementUpdateSignals(
        full_requirement="Build an ADC review GDA including entity country."
    )
    client = SimpleNamespace(
        aio=SimpleNamespace(
            models=StubModels(SimpleNamespace(parsed=signals, text=None))
        )
    )
    updater = GeminiRequirementUpdater(
        api_key="test",
        model="gemini-test",
        client=client,
    )

    result = asyncio.run(
        updater.update(
            previous_requirement="Build an ADC review GDA.",
            supplemental_information="Include entity country.",
            feedback=[],
            previous_output=None,
        )
    )

    assert result == signals


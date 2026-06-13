import asyncio
from types import SimpleNamespace

from analyze_agent.adapters.gemini_knowledge_reconstructor import (
    GeminiKnowledgeReconstructor,
)
from analyze_agent.domain.models import (
    AnalyzedRequirement,
    KnowledgeChunk,
    KnowledgeReuseSignals,
)


class StubModels:
    def __init__(self, response) -> None:
        self.response = response

    async def generate_content(self, **kwargs):
        return self.response


def test_gemini_reconstructor_returns_typed_signals() -> None:
    signals = KnowledgeReuseSignals()
    client = SimpleNamespace(
        aio=SimpleNamespace(
            models=StubModels(SimpleNamespace(parsed=signals, text=None))
        )
    )
    reconstructor = GeminiKnowledgeReconstructor(
        api_key="test",
        model="gemini-test",
        client=client,
    )

    result = asyncio.run(
        reconstructor.reconstruct(
            requirement="Build an ADC GDA.",
            analyzed_requirement=AnalyzedRequirement(
                summary="Build an ADC GDA.",
                business_goal="Support ADC review.",
            ),
            chunks=[KnowledgeChunk(chunk_id="chunk-1", text="ADC context")],
        )
    )

    assert result == signals


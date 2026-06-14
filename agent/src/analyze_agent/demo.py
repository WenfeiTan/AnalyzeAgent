"""Public Fake Knowledge Base scenarios for local development jobs."""

from __future__ import annotations

from enum import StrEnum

from analyze_agent.adapters.fake_knowledge_retriever import (
    FakeKnowledgeBaseRetriever,
    FakeRetrievalScenario,
)
from analyze_agent.config import Settings, load_settings
from analyze_agent.domain.models import KnowledgeChunk
from analyze_agent.facade import AnalyzeAgent
from analyze_agent.ports.retriever_errors import (
    InvalidKnowledgeResponse,
    KnowledgeRetrievalTimeout,
)
from analyze_agent.runtime import build_runtime


class DemoKnowledgeScenario(StrEnum):
    EMPTY = "empty"
    COMPLETE_MAPPING = "complete_mapping"
    PARTIAL_MAPPING = "partial_mapping"
    NO_EVIDENCE = "no_evidence"
    TIMEOUT = "timeout"
    INVALID = "invalid"


def create_demo_agent(
    scenario: DemoKnowledgeScenario | str = DemoKnowledgeScenario.EMPTY,
    *,
    settings: Settings | None = None,
) -> AnalyzeAgent:
    resolved = settings or load_settings(require_api_key=True)
    selected = DemoKnowledgeScenario(scenario)
    retriever = FakeKnowledgeBaseRetriever(
        default_scenario=_scenario(selected)
    )
    return AnalyzeAgent(build_runtime(resolved, retriever=retriever))


def _scenario(selected: DemoKnowledgeScenario) -> FakeRetrievalScenario:
    if selected is DemoKnowledgeScenario.EMPTY:
        return FakeRetrievalScenario()
    if selected is DemoKnowledgeScenario.TIMEOUT:
        return FakeRetrievalScenario(error=KnowledgeRetrievalTimeout())
    if selected is DemoKnowledgeScenario.INVALID:
        return FakeRetrievalScenario(
            error=InvalidKnowledgeResponse("Fake Knowledge Base returned invalid data.")
        )
    if selected is DemoKnowledgeScenario.NO_EVIDENCE:
        return FakeRetrievalScenario(
            chunks=(
                KnowledgeChunk(
                    chunk_id="demo-no-evidence",
                    text="A general ADC glossary entry without a verified mapping.",
                    metadata={"case_status": "reference"},
                ),
            )
        )
    if selected is DemoKnowledgeScenario.PARTIAL_MAPPING:
        return FakeRetrievalScenario(
            chunks=(
                KnowledgeChunk(
                    chunk_id="demo-partial-mapping",
                    text=(
                        "A prior ADC review mentioned ADC_entity_country and "
                        "entity_country, but did not identify a source asset."
                    ),
                    metadata={"case_status": "partial"},
                ),
            )
        )
    return FakeRetrievalScenario(
        chunks=(
            KnowledgeChunk(
                chunk_id="demo-complete-mapping",
                text=(
                    "Successful ADC review mapping: ADC_entity_country uses "
                    "attribute entity_country from asset adc_entity."
                ),
                metadata={"case_status": "success"},
            ),
        )
    )

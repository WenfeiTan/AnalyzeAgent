"""Public Fake Knowledge Base scenarios for local development jobs."""

from __future__ import annotations

import json
from enum import StrEnum
from importlib.resources import files

from analyze_agent.adapters.fake_knowledge_retriever import (
    FakeKnowledgeBaseRetriever,
    FakeRetrievalScenario,
    parse_fake_scenario,
)
from analyze_agent.config import Settings, load_settings
from analyze_agent.facade import AnalyzeAgent
from analyze_agent.ports.retriever_errors import InvalidKnowledgeResponse
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
        default_scenario=load_demo_scenario(selected)
    )
    return AnalyzeAgent(build_runtime(resolved, retriever=retriever))


def load_demo_scenario(
    scenario: DemoKnowledgeScenario | str,
) -> FakeRetrievalScenario:
    selected = DemoKnowledgeScenario(scenario)
    resource = files("analyze_agent.demo_resources").joinpath(
        f"{selected.value}.json"
    )
    try:
        payload = json.loads(resource.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InvalidKnowledgeResponse(
            f"Unable to load packaged demo scenario {selected.value}: {error}"
        ) from error
    return parse_fake_scenario(payload)

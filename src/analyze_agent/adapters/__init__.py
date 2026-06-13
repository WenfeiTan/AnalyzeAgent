"""Infrastructure adapters."""

from analyze_agent.adapters.fake_knowledge_retriever import (
    FakeKnowledgeBaseRetriever,
    load_fake_scenario,
)

__all__ = ["FakeKnowledgeBaseRetriever", "load_fake_scenario"]


import asyncio
from pathlib import Path

from analyze_agent import (
    DemoKnowledgeScenario,
    Settings,
    create_demo_agent,
)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        google_api_key="test-placeholder",
        model="gemini-test",
        log_level="INFO",
        database_path=tmp_path / "demo.sqlite3",
    )


def test_demo_agents_have_isolated_retrieval_scenarios(tmp_path: Path) -> None:
    empty = create_demo_agent(
        DemoKnowledgeScenario.EMPTY,
        settings=_settings(tmp_path),
    )
    complete = create_demo_agent(
        DemoKnowledgeScenario.COMPLETE_MAPPING,
        settings=_settings(tmp_path),
    )

    empty_chunks = asyncio.run(empty.search_knowledge_base("ADC requirement"))
    complete_chunks = asyncio.run(
        complete.search_knowledge_base("ADC requirement")
    )

    assert empty_chunks == []
    assert complete_chunks[0].chunk_id == "demo-complete-mapping"

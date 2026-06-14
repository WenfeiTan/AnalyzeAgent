from google.adk.agents import Agent

from analyze_agent.agent import root_agent


def test_root_agent_is_registered() -> None:
    assert isinstance(root_agent, Agent)
    assert root_agent.name == "analyze_agent"


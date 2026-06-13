"""Google ADK entrypoint for the Analyze Agent."""

from google.adk.agents import Agent

from analyze_agent.config import load_settings

_settings = load_settings(require_api_key=False)

root_agent = Agent(
    name="analyze_agent",
    model=_settings.model,
    description="Analyzes Asset Discovery requirements into structured search guidance.",
    instruction=(
        "You are the Analyze Agent for Asset Discovery. "
        "The bootstrap implementation only verifies the ADK entrypoint; "
        "domain workflows are added in later development branches."
    ),
)


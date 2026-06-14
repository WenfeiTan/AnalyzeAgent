"""Google ADK entrypoint for the Analyze Agent."""

from google.adk.agents import Agent

from analyze_agent.config import load_settings
from analyze_agent.tools import (
    analyze_initial,
    analyze_update,
    search_knowledge_base,
)

_settings = load_settings(require_api_key=False)

root_agent = Agent(
    name="analyze_agent",
    model=_settings.model,
    description="Analyzes Asset Discovery requirements into structured search guidance.",
    instruction=(
        "You are the Analyze Agent for Asset Discovery. "
        "For a new requirement, call analyze_initial. "
        "For supplemental information or feedback tied to an existing "
        "requirement_id, call analyze_update. "
        "Use search_knowledge_base only when explicitly inspecting retrieval. "
        "Return tool results without inventing fields, mappings, confidence, "
        "priorities, assets, attributes, or revision identifiers."
    ),
    tools=[analyze_initial, analyze_update, search_knowledge_base],
)

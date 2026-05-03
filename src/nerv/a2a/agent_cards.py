from __future__ import annotations

from nerv.config import RuntimeSettings
from nerv.models.a2a import AgentCapabilities, AgentSkill, NervAgentCard


def hub_agent_card(settings: RuntimeSettings) -> NervAgentCard:
    return NervAgentCard(
        name="nerv-hub",
        description="Orchestration hub - routes tasks between agents.",
        url=settings.a2a_base_url,
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id="orchestration",
                name="Task Orchestration",
                description="Route tasks to the best-fit agent based on skill matching.",
            ),
        ],
    )


def opencode_agent_card(settings: RuntimeSettings) -> NervAgentCard:
    return NervAgentCard(
        name="opencode",
        description="Code generation, implementation, refactoring, and plan execution agent.",
        url=f"{settings.a2a_base_url}/agents/opencode",
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id="implementation",
                name="Code Implementation",
                description="Generate production code from designs, specs, or instructions.",
            ),
            AgentSkill(
                id="refactoring",
                name="Code Refactoring",
                description="Restructure existing code while preserving behavior.",
            ),
            AgentSkill(
                id="file-ops",
                name="File Operations",
                description="Create, move, rename, and bulk-edit files across the project tree.",
            ),
            AgentSkill(
                id="plan-execution",
                name="Plan Execution",
                description="Execute step-by-step implementation plans.",
            ),
        ],
    )


def default_agent_cards(settings: RuntimeSettings) -> dict[str, NervAgentCard]:
    return {
        "hub": hub_agent_card(settings),
        "opencode": opencode_agent_card(settings),
    }


def load_agent_cards(settings: RuntimeSettings) -> dict[str, NervAgentCard]:
    return default_agent_cards(settings)

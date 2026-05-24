from __future__ import annotations

from nerv.a2a.agent_cards import (
    default_agent_cards,
    hub_agent_card,
    opencode_agent_card,
    sdd_archiver_card,
    sdd_designer_card,
    sdd_explorer_card,
    sdd_proposer_card,
    sdd_speccer_card,
    sdd_task_planner_card,
    sdd_verifier_card,
)

SDD_AGENTS = {
    "sdd-explorer",
    "sdd-proposer",
    "sdd-speccer",
    "sdd-designer",
    "sdd-task-planner",
    "sdd-verifier",
    "sdd-archiver",
}


def test_default_agent_cards(runtime_settings) -> None:
    cards = default_agent_cards(runtime_settings)

    expected = {"hub", "opencode"} | SDD_AGENTS
    assert set(cards) == expected
    assert cards["hub"].name == "nerv-hub"
    assert cards["opencode"].skills[0].id == "implementation"
    assert cards["hub"].capabilities.model_dump() == {"streaming": True}
    assert "authentication" not in cards["hub"].model_dump()


def test_card_urls_are_localhost(runtime_settings) -> None:
    assert str(hub_agent_card(runtime_settings).url).rstrip("/") == runtime_settings.a2a_base_url
    assert str(opencode_agent_card(runtime_settings).url).startswith(
        f"{runtime_settings.a2a_base_url}/"
    )


def test_sdd_explorer_card(runtime_settings) -> None:
    card = sdd_explorer_card(runtime_settings)
    assert card.name == "nerv-sdd-explorer"
    assert len(card.skills) == 1
    assert card.skills[0].id == "sdd-explore"
    assert not card.capabilities.streaming


def test_sdd_proposer_card(runtime_settings) -> None:
    card = sdd_proposer_card(runtime_settings)
    assert card.name == "nerv-sdd-proposer"
    assert card.skills[0].id == "sdd-propose"


def test_sdd_speccer_card(runtime_settings) -> None:
    card = sdd_speccer_card(runtime_settings)
    assert card.name == "nerv-sdd-speccer"
    assert card.skills[0].id == "sdd-spec"


def test_sdd_designer_card(runtime_settings) -> None:
    card = sdd_designer_card(runtime_settings)
    assert card.name == "nerv-sdd-designer"
    assert card.skills[0].id == "sdd-design"


def test_sdd_task_planner_card(runtime_settings) -> None:
    card = sdd_task_planner_card(runtime_settings)
    assert card.name == "nerv-sdd-task-planner"
    assert card.skills[0].id == "sdd-tasks"


def test_sdd_verifier_card(runtime_settings) -> None:
    card = sdd_verifier_card(runtime_settings)
    assert card.name == "nerv-sdd-verifier"
    assert card.skills[0].id == "sdd-verify"


def test_sdd_archiver_card(runtime_settings) -> None:
    card = sdd_archiver_card(runtime_settings)
    assert card.name == "nerv-sdd-archiver"
    assert card.skills[0].id == "sdd-archive"


def test_sdd_cards_have_valid_urls(runtime_settings) -> None:
    factories = [
        sdd_explorer_card,
        sdd_proposer_card,
        sdd_speccer_card,
        sdd_designer_card,
        sdd_task_planner_card,
        sdd_verifier_card,
        sdd_archiver_card,
    ]
    for factory in factories:
        card = factory(runtime_settings)
        assert str(card.url).startswith(str(runtime_settings.a2a_base_url))


def test_sdd_cards_present_in_default(runtime_settings) -> None:
    cards = default_agent_cards(runtime_settings)
    for agent_id in SDD_AGENTS:
        assert agent_id in cards, f"Missing SDD agent card: {agent_id}"
        assert cards[agent_id].skills, f"SDD card {agent_id} has no skills"
        assert cards[agent_id].name, f"SDD card {agent_id} has no name"

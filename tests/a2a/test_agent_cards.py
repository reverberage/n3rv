from __future__ import annotations

from nerv.a2a.agent_cards import (
    default_agent_cards,
    hub_agent_card,
    opencode_agent_card,
)


def test_default_agent_cards(runtime_settings) -> None:
    cards = default_agent_cards(runtime_settings)

    assert set(cards) == {"hub", "opencode"}
    assert cards["hub"].name == "nerv-hub"
    assert cards["opencode"].skills[0].id == "implementation"
    assert cards["hub"].capabilities.model_dump() == {"streaming": True}
    assert "authentication" not in cards["hub"].model_dump()


def test_card_urls_are_localhost(runtime_settings) -> None:
    assert (
        str(hub_agent_card(runtime_settings).url).rstrip("/")
        == runtime_settings.a2a_base_url
    )
    assert str(opencode_agent_card(runtime_settings).url).startswith(
        f"{runtime_settings.a2a_base_url}/"
    )

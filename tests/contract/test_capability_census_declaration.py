"""Local invariants for the ADR-SHARED-029 Pulse capability declaration."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DECLARATION = ROOT / ".baobab" / "capability-provider.yaml"


def test_census_declares_contracted_intent_without_provider_support() -> None:
    declaration = yaml.safe_load(DECLARATION.read_text())

    assert declaration["engine"]["engine_id"] == "baobab-pulse"
    assert not declaration.get("providers")

    planned = declaration.get("planned_capabilities") or []
    assert {
        item["capability_key"]: item["proposal_status"]
        for item in planned
    } == {
        "intelligence.evidence.search": "CONTRACTED",
        "intelligence.research-mission.manage": "CONTRACTED",
    }

    for item in planned:
        assert "proposed_key" not in item
        assert item["provenance"]["authority"] == {
            "repository": "baobab-platform/shared",
            "decision": "ADR-SHARED-029",
        }


def test_census_does_not_leak_implementation_or_foreign_authority() -> None:
    text = DECLARATION.read_text().lower()
    for forbidden_key in (
        "pulse.evidence.search",
        "haystack.",
        "qdrant.",
        "intelligence.regulatory.query",
        "intelligence.trade-document",
    ):
        assert forbidden_key not in text

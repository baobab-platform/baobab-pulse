"""P-CAP-06 invariants for the Pulse capability-provider declaration."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DECLARATION = ROOT / ".baobab" / "capability-provider.yaml"

EXPECTED_CAPABILITIES = {
    "intelligence.evidence.search",
    "intelligence.research-mission.manage",
}


def _declaration() -> dict[str, object]:
    value = yaml.safe_load(DECLARATION.read_text())
    assert isinstance(value, dict)
    return value


def test_p_cap_06_promotes_both_canonical_capabilities_to_partial_support() -> None:
    declaration = _declaration()

    assert declaration["engine"]["engine_id"] == "baobab-pulse"
    assert not declaration.get("planned_capabilities")

    providers = declaration.get("providers") or []
    assert len(providers) == 1
    provider = providers[0]
    assert provider["provider_key"] == "baobab-pulse.core"
    assert provider["provider_type"] == "BAOBAB_ENGINE"
    assert provider["implementation_key"] == "core"
    assert provider["simulated"] is False
    assert provider["production_permitted"] is True

    support = provider["support"]
    assert {item["capability_key"] for item in support} == EXPECTED_CAPABILITIES
    assert {item["implementation_status"] for item in support} == {"PARTIAL"}

    for item in support:
        assert item["contract_versions"] == [1]
        assert item["provenance"]["authority"] == {
            "repository": "baobab-platform/shared",
            "decision": "ADR-SHARED-029",
        }
        evidence = item["implementation_evidence"]
        assert evidence
        for entry in evidence:
            path = ROOT / entry["path"]
            assert path.exists(), f"declared implementation evidence is missing: {path}"


def test_p_cap_06_does_not_overclaim_implemented_or_activation_authority() -> None:
    declaration = _declaration()
    provider = declaration["providers"][0]
    assert all(
        item["implementation_status"] != "IMPLEMENTED"
        for item in provider["support"]
    )

    text = DECLARATION.read_text().lower()
    for forbidden_key in (
        "pulse.evidence.search",
        "haystack.",
        "qdrant.",
        "intelligence.regulatory.query",
        "intelligence.trade-document",
        "certified:",
        "active:",
        "bindings:",
        "grants:",
    ):
        assert forbidden_key not in text

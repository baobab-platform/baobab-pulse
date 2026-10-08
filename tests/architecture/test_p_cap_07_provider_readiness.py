"""P-CAP-07 readiness invariants as refined by P-CAP-08 activation governance."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SHARED_PROVIDER_AUTHORITY_REVISION = "f61de9c5141e432b32cc3b585aafa7d1b6727716"
CAPABILITIES = {
    "intelligence.evidence.search",
    "intelligence.research-mission.manage",
}


def test_repository_remains_active_engine_with_implemented_provider_support() -> None:
    repository = yaml.safe_load((ROOT / ".baobab" / "repository.yaml").read_text())
    declaration = yaml.safe_load(
        (ROOT / ".baobab" / "capability-provider.yaml").read_text()
    )

    assert repository["repository"]["lifecycle"] == "active"
    assert "engine" in repository["capabilities"]

    providers = declaration["providers"]
    assert len(providers) == 1
    provider = providers[0]
    assert provider["provider_key"] == "baobab-pulse.core"
    assert provider["simulated"] is False
    assert provider["production_permitted"] is True
    assert provider["invocation"] == {
        "service_reference": "service://baobab-pulse/capabilities",
        "protocol": "http",
    }

    support = {item["capability_key"]: item for item in provider["support"]}
    assert set(support) == CAPABILITIES
    for capability_key in CAPABILITIES:
        item = support[capability_key]
        assert item["contract_versions"] == [1]
        assert item["implementation_status"] == "IMPLEMENTED"
        assert item["provenance"]["authority"] == {
            "repository": "baobab-platform/shared",
            "decision": "ADR-SHARED-032",
        }
        assert item["provenance"]["source_revision"] == SHARED_PROVIDER_AUTHORITY_REVISION
        evidence_types = {evidence["type"] for evidence in item["implementation_evidence"]}
        assert {"source", "contract-test", "integration-test"} <= evidence_types

    planned = declaration.get("planned_capabilities", [])
    assert CAPABILITIES.isdisjoint(
        {item.get("capability_key") for item in planned}
    )


def test_p_cap_08_authority_contracts_refine_the_p_cap_07_readiness_boundary() -> None:
    lock = yaml.safe_load((ROOT / "contracts.lock.yaml").read_text())
    assert lock["source"]["commit"] == SHARED_PROVIDER_AUTHORITY_REVISION
    contracts = set(lock["contracts"])
    assert "contracts/authorization/v1/scope-registry.yaml" in contracts
    assert "contracts/identity/v1/workload-registry.yaml" in contracts
    assert "contracts/intelligence/v1/capabilities.yaml" in contracts
    assert "contracts/control-plane/v1/platform-context.schema.json" in contracts

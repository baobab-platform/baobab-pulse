"""P-CAP-08 contract adoption and certification-handoff invariants.

Pulse owns implementation evidence. Shared owns canonical capability semantics and
EA-09 governance. Control Plane owns certification and provider activation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/contracts"


def _json(relative: str) -> dict:
    value = json.loads((FIXTURES / relative).read_text())
    assert isinstance(value, dict)
    return value


def _text(relative: str) -> str:
    return (FIXTURES / relative).read_text()


def _yaml_item(text: str, marker: str) -> str:
    """Return one top-level list item block starting at marker."""
    start = text.index(marker)
    tail = text[start:]
    match = re.search(r"\n  - name: |\n  - capability_key: ", tail[len(marker) :])
    return tail if match is None else tail[: len(marker) + match.start()]


def test_shared_admits_first_intelligence_tranche_without_promoting_maturity() -> None:
    capabilities = _text("intelligence/v1/capabilities.yaml")

    assert capabilities.count("lifecycle: ACTIVE") == 2
    assert capabilities.count("maturity: EXPERIMENTAL") == 2
    assert capabilities.count("authority: ADR-SHARED-032") == 2
    assert capabilities.count(
        "provider_implementation: p-cap-08-certification-activation-governed"
    ) == 2


def test_shared_registration_keeps_pulse_provider_draft() -> None:
    registration = _json("intelligence/v1/pulse-registration.json")

    assert registration["repository"] == "baobab-pulse"
    assert registration["provider"] == {
        "provider_key": "baobab-pulse.core",
        "name": "Baobab Pulse core provider",
        "provider_type": "BAOBAB_ENGINE",
        "engine_key": "core",
        "lifecycle": "DRAFT",
        "ownership": "baobab-pulse",
        "simulated": False,
        "production_permitted": True,
        "invocation": {
            "service_reference": "service://baobab-pulse/capabilities",
            "protocol": "http",
        },
    }
    assert {
        (item["capability_key"], tuple(item["contract_versions"]))
        for item in registration["support"]
    } == {
        ("intelligence.evidence.search", (1,)),
        ("intelligence.research-mission.manage", (1,)),
    }


def test_ea09_certification_is_release_bound_and_content_addressed() -> None:
    schema = _json("capability/v1/certification.schema.json")
    request = schema["$defs"]["ProviderCapabilityCertificationRecordRequest"]
    evidence = schema["$defs"]["CertificationEvidence"]

    assert set(request["required"]) == {
        "provider_id",
        "capability_key",
        "contract_version",
        "release_id",
        "qualification_profile",
        "evidence",
        "reason",
    }
    assert request["properties"]["release_id"]["$ref"].endswith(
        "control-plane/v1/domain.schema.json#/$defs/engineReleaseId"
    )
    assert evidence["properties"]["uri"]["pattern"] == "^(?:https|oci)://"
    assert evidence["properties"]["digest"]["pattern"] == "^sha256:[0-9a-f]{64}$"
    assert {"CONTRACT_TEST", "INTEGRATION_TEST", "SECURITY_REVIEW", "OPERABILITY_REVIEW"} <= set(
        schema["$defs"]["evidenceType"]["enum"]
    )


def test_production_requires_certification_but_nonproduction_does_not() -> None:
    policy = _text("topology/v1/release-policy.yaml")
    certification = policy.split("certification_required:", 1)[1].split("\n\n", 1)[0]

    assert "local: false" in certification
    assert "development: false" in certification
    assert "staging: false" in certification
    assert "production: true" in certification


def test_provider_certification_scope_is_human_only_control_plane_authority() -> None:
    scopes = _text("authorization/v1/scope-registry.yaml")
    block = _yaml_item(scopes, '  - name: "provider:certify"')

    assert 'audience: ["baobab-control-plane"]' in block
    assert 'allowed_actors: ["human"]' in block
    assert "privileged: true" in block
    assert 'audience: ["baobab-pulse"]' not in block
    assert 'allowed_actors: ["workload"]' not in block


def test_pulse_declaration_claims_implementation_not_certification_or_activation() -> None:
    declaration = (ROOT / ".baobab/capability-provider.yaml").read_text()

    assert declaration.count("implementation_status: IMPLEMENTED") == 2
    assert "production_permitted: true" in declaration
    assert "decision: ADR-SHARED-032" in declaration
    assert (
        "source_revision: f61de9c5141e432b32cc3b585aafa7d1b6727716"
        in declaration
    )
    # Provider lifecycle is intentionally absent from the repository declaration:
    # Shared registration creates DRAFT; Control Plane changes it under governance.
    assert re.search(r"^\s+lifecycle:", declaration, flags=re.MULTILINE) is None
    assert re.search(r"^\s+certification", declaration, flags=re.MULTILINE) is None


def test_research_mission_event_is_still_not_part_of_p_cap_08_activation() -> None:
    declaration = (ROOT / ".baobab/capability-provider.yaml").read_text()
    assert "HELD_UNREGISTERED" in declaration

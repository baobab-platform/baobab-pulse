"""Shared-contract conformance for P-CAP-04 ResearchMission management."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from baobab_pulse.contracts.api.research_missions import (
    ResearchMissionCreateRequest,
    ResearchMissionGetRequest,
    ResearchMissionResponse,
)
from baobab_pulse.domain.research import ResearchMission
from baobab_pulse.domain.shared.enums import Classification, ConfidenceBand, TenantScope
from baobab_pulse.domain.shared.value_objects import TenantContext

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "tests/fixtures/contracts/intelligence/v1/domain.schema.json"


def _schema() -> dict:
    value = json.loads(SCHEMA_PATH.read_text())
    assert isinstance(value, dict)
    return value


def _validate(def_name: str, instance: dict) -> None:
    schema = _schema()
    Draft202012Validator(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": schema["$defs"],
            **schema["$defs"][def_name],
        }
    ).validate(instance)


def test_create_request_matches_shared_v1_and_carries_no_tenant_authority() -> None:
    schema = _schema()["$defs"]["researchMissionCreateRequest"]

    assert set(schema["properties"]) == {
        "operation",
        "title",
        "research_question",
        "tenant_scope",
        "classification",
        "confidence_requirement",
    }
    assert "tenant_id" not in schema["properties"]
    assert "context_id" not in schema["properties"]

    request = ResearchMissionCreateRequest(
        operation="CREATE",
        title="Uganda coffee corridor research",
        research_question="What changed in the Uganda to South Africa coffee corridor?",
        tenant_scope=TenantScope.TENANT,
        classification=Classification.TENANT,
        confidence_requirement=ConfidenceBand.MODERATE,
    )
    _validate(
        "researchMissionCreateRequest",
        request.model_dump(mode="json"),
    )


def test_get_request_matches_shared_v1() -> None:
    request = ResearchMissionGetRequest(
        operation="GET",
        research_mission_id="rms_1234567890abcdef1234567890abcdef",
    )
    _validate("researchMissionGetRequest", request.model_dump(mode="json"))


def test_response_matches_shared_v1_including_confidence_requirement() -> None:
    mission = ResearchMission(
        id="rms_1234567890abcdef1234567890abcdef",
        title="Uganda coffee corridor research",
        research_question="What changed?",
        tenant_scope=TenantScope.TENANT,
        tenant_context=TenantContext(tenant_id="tn_test"),
        classification=Classification.TENANT,
        confidence_requirement=ConfidenceBand.HIGH,
    )

    response = ResearchMissionResponse.from_domain(mission)
    instance = response.model_dump(mode="json")
    _validate("researchMissionResponse", instance)

    assert instance["confidence_requirement"] == "HIGH"

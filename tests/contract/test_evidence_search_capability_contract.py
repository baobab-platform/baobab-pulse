"""Shared-contract conformance for P-CAP-03 intelligence.evidence.search."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from baobab_pulse.contracts.api.evidence import (
    EvidenceSearchRequest,
    EvidenceSearchResponse,
)

ROOT = Path(__file__).resolve().parents[2]
INTELLIGENCE_SCHEMA = (
    ROOT / "tests/fixtures/contracts/intelligence/v1/domain.schema.json"
)
PLATFORM_CONTEXT_SCHEMA = (
    ROOT / "tests/fixtures/contracts/control-plane/v1/platform-context.schema.json"
)
WORKLOAD_TOKEN_SCHEMA = (
    ROOT / "tests/fixtures/contracts/identity/v1/workload-token-response.schema.json"
)


def _schema(path: Path) -> dict:
    value = json.loads(path.read_text())
    assert isinstance(value, dict)
    return value


def test_request_model_is_exact_shared_body_shape() -> None:
    schema = _schema(INTELLIGENCE_SCHEMA)
    request_schema = schema["$defs"]["evidenceSearchRequest"]

    assert set(request_schema["required"]) == {"query_text"}
    assert set(request_schema["properties"]) == {
        "query_text",
        "evidence_set_id",
        "top_k",
    }
    assert "tenant_id" not in request_schema["properties"]
    assert "requester_clearance" not in request_schema["properties"]

    instance = EvidenceSearchRequest(
        query_text="coffee exports",
        evidence_set_id="evs_test",
        top_k=7,
    ).model_dump(mode="json", exclude_none=True)
    Draft202012Validator(request_schema).validate(instance)


def test_response_model_is_exact_shared_candidate_shape() -> None:
    schema = _schema(INTELLIGENCE_SCHEMA)
    response_schema = schema["$defs"]["evidenceSearchResponse"]

    instance = EvidenceSearchResponse(candidates=()).model_dump(mode="json")
    Draft202012Validator(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": schema["$defs"],
            **response_schema,
        }
    ).validate(instance)

    candidate = schema["$defs"]["evidenceCandidate"]
    assert set(candidate["required"]) == {
        "canonical_object_id",
        "evidence_set_id",
        "score",
        "is_stale",
    }
    assert "confidence" not in candidate["properties"]
    assert "quality" not in candidate["properties"]


def test_current_authority_contracts_do_not_invent_classification_clearance() -> None:
    context = _schema(PLATFORM_CONTEXT_SCHEMA)["$defs"]["PlatformContextValidation"]
    workload = _schema(WORKLOAD_TOKEN_SCHEMA)["$defs"]["WorkloadTokenClaims"]

    assert "classification_clearance" not in context["properties"]
    assert "classification_clearance" not in workload["properties"]
    assert "clearance" not in context["properties"]
    assert "clearance" not in workload["properties"]

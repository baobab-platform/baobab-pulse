"""Contract conformance for RTD-09 consumer models against pinned Shared schemas."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError
from referencing import Registry, Resource

from baobab_pulse.contracts.upstream_events import (
    DocumentRequirementsDeterminedData,
    DocumentVersionValidityChangedData,
    DocumentVersionVerificationChangedData,
    RegulatoryEvidenceOfferedData,
    RequirementSatisfactionEvaluatedData,
)
from baobab_pulse.domain.shared.value_objects import (
    CrossEngineObjectReference,
    CrossEngineReferenceMode,
    CrossEngineReferenceScope,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "contracts"
TENANT = "tn_test01"


def _registry() -> Registry:
    resources: list[tuple[str, Resource]] = []
    for path in FIXTURES.rglob("*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        schema_id = doc.get("$id")
        if schema_id:
            resources.append((schema_id, Resource.from_contents(doc)))
    return Registry().with_resources(resources)


def _validate(schema_path: Path, ref: str, instance: object) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(
        {"$ref": f"{schema['$id']}#{ref}"},
        registry=_registry(),
        format_checker=FormatChecker(),
    )
    validator.validate(instance)


def _ref(owner: str, object_type: str, object_id: str) -> CrossEngineObjectReference:
    return CrossEngineObjectReference(
        owner_engine_id=owner,
        object_type=object_type,
        object_id=object_id,
        reference_mode=CrossEngineReferenceMode.IDENTITY_PINNED,
        scope=CrossEngineReferenceScope.TENANT,
        tenant_id=TENANT,
    )


def test_cross_engine_reference_matches_pinned_shared_schema() -> None:
    reference = _ref("baobab-regulations", "REGULATORY_DECISION", "regdec_01")
    _validate(
        FIXTURES / "cross-engine-reference" / "v1" / "domain.schema.json",
        "/$defs/crossEngineObjectReference",
        reference.model_dump(mode="json", exclude_none=True),
    )


def test_regulations_requirement_event_payload_matches_pinned_shared_schema() -> None:
    decision = _ref("baobab-regulations", "REGULATORY_DECISION", "regdec_01")
    payload = DocumentRequirementsDeterminedData.model_validate(
        {
            "tenant_id": TENANT,
            "requirement_set": {
                "regulatory_decision_reference": decision.model_dump(mode="json"),
                "requirements": [
                    {
                        "requirement_reference": _ref(
                            "baobab-regulations", "DOCUMENT_REQUIREMENT", "regreq_01"
                        ).model_dump(mode="json"),
                        "regulatory_decision_reference": decision.model_dump(mode="json"),
                        "requirement_kind": "DOCUMENT",
                        "requirement_code": "PHYTOSANITARY_CERTIFICATE_REQUIRED",
                        "purpose_code": "SPS",
                        "acceptable_document_types": ["PHYTOSANITARY_CERTIFICATE"],
                        "required_issuer_roles": ["COMPETENT_AUTHORITY"],
                        "required_data_elements": ["CONSIGNMENT_REFERENCE"],
                        "unsatisfied_effect_code": "SPS_HOLD_REQUIRED",
                        "effective_from": "2026-10-06T00:00:00Z",
                        "effective_to": None,
                        "determined_at": "2026-10-06T12:00:00Z",
                    }
                ],
                "legal_time": "2026-10-06T10:00:00Z",
                "knowledge_time": "2026-10-06T12:00:00Z",
                "determined_at": "2026-10-06T12:00:00Z",
            },
        }
    )
    _validate(
        FIXTURES / "regulatory-document-exchange" / "v1" / "events.schema.json",
        "/$defs/documentRequirementsDeterminedEventData",
        payload.model_dump(mode="json", exclude_none=True),
    )


def test_regulations_satisfaction_payload_matches_pinned_shared_schema() -> None:
    payload = RequirementSatisfactionEvaluatedData.model_validate(
        {
            "tenant_id": TENANT,
            "result": {
                "assessment_reference": _ref(
                    "baobab-regulations", "REGULATORY_EVIDENCE_ASSESSMENT", "regassess_01"
                ).model_dump(mode="json"),
                "regulatory_decision_reference": _ref(
                    "baobab-regulations", "REGULATORY_DECISION", "regdec_01"
                ).model_dump(mode="json"),
                "requirement_reference": _ref(
                    "baobab-regulations", "DOCUMENT_REQUIREMENT", "regreq_01"
                ).model_dump(mode="json"),
                "outcome": "SATISFIED",
                "accepted_document_version_references": [
                    _ref("baobab-trade-docs", "DOCUMENT_VERSION", "tdocv_001").model_dump(
                        mode="json"
                    )
                ],
                "rejected_evidence": [],
                "reason_codes": ["DOCUMENT_ACCEPTED"],
                "resulting_regulatory_decision_reference": None,
                "evaluated_at": "2026-10-06T12:00:00Z",
            },
        }
    )
    _validate(
        FIXTURES / "regulatory-document-exchange" / "v1" / "events.schema.json",
        "/$defs/requirementSatisfactionEvaluatedEventData",
        payload.model_dump(mode="json", exclude_none=True),
    )


def test_trade_docs_evidence_offered_payload_matches_pinned_shared_schema() -> None:
    payload = RegulatoryEvidenceOfferedData.model_validate(
        {
            "tenant_id": TENANT,
            "regulatory_decision_reference": _ref(
                "baobab-regulations", "REGULATORY_DECISION", "regdec_01"
            ).model_dump(mode="json"),
            "requirement_reference": _ref(
                "baobab-regulations", "DOCUMENT_REQUIREMENT", "regreq_01"
            ).model_dump(mode="json"),
            "document_version_references": [
                _ref("baobab-trade-docs", "DOCUMENT_VERSION", "tdocv_001").model_dump(mode="json")
            ],
            "offered_at": "2026-10-06T12:00:00Z",
        }
    )
    _validate(
        FIXTURES / "regulatory-document-exchange" / "v1" / "events.schema.json",
        "/$defs/documentRegulatoryEvidenceOfferedEventData",
        payload.model_dump(mode="json", exclude_none=True),
    )


@pytest.mark.parametrize(
    ("model", "ref", "payload"),
    [
        (
            DocumentVersionVerificationChangedData,
            "/$defs/documentVersionVerificationChangedEventData",
            {
                "trade_document_id": "tdoc_001",
                "document_version_id": "tdocv_001",
                "tenant_id": TENANT,
                "previous_verification_state": "PENDING",
                "verification_state": "VERIFIED",
                "reason_code": "SIGNATURE_VERIFIED",
                "changed_at": "2026-10-06T12:00:00Z",
            },
        ),
        (
            DocumentVersionValidityChangedData,
            "/$defs/documentVersionValidityChangedEventData",
            {
                "trade_document_id": "tdoc_001",
                "document_version_id": "tdocv_001",
                "tenant_id": TENANT,
                "previous_temporal_validity_state": "CURRENTLY_VALID",
                "temporal_validity_state": "EXPIRED",
                "authority_reference": None,
                "basis_reference": None,
                "changed_at": "2026-10-06T12:00:00Z",
            },
        ),
    ],
)
def test_trade_document_event_payload_matches_pinned_shared_schema(
    model: type[DocumentVersionVerificationChangedData] | type[DocumentVersionValidityChangedData],
    ref: str,
    payload: dict[str, object],
) -> None:
    parsed = model.model_validate(payload)
    _validate(
        FIXTURES / "trade-document" / "v2" / "events.schema.json",
        ref,
        parsed.model_dump(mode="json", exclude_none=True),
    )


def test_consumer_rejects_shapes_shared_rejects() -> None:
    with pytest.raises(ValidationError):
        DocumentVersionVerificationChangedData.model_validate(
            {
                "trade_document_id": "wrong_01",
                "document_version_id": "tdocv_001",
                "tenant_id": TENANT,
                "verification_state": "VERIFIED",
                "changed_at": "2026-10-06T12:00:00Z",
            }
        )

    with pytest.raises(ValidationError):
        RegulatoryEvidenceOfferedData.model_validate(
            {
                "tenant_id": TENANT,
                "regulatory_decision_reference": _ref(
                    "baobab-regulations", "REGULATORY_DECISION", "regdec_01"
                ).model_dump(mode="json"),
                "requirement_reference": _ref(
                    "baobab-regulations", "DOCUMENT_REQUIREMENT", "regreq_01"
                ).model_dump(mode="json"),
                "document_version_references": [],
                "offered_at": "2026-10-06T12:00:00Z",
            }
        )

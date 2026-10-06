from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from baobab_pulse.application.services.upstream_fact_projection_service import (
    DOCUMENTS_VERIFICATION,
    REGULATIONS_SATISFACTION,
    UpstreamFactProjectionService,
)
from baobab_pulse.contracts.upstream_events import UpstreamEventEnvelope
from baobab_pulse.domain.projections import UpstreamFactKind
from baobab_pulse.domain.shared.errors import InvariantViolation
from baobab_pulse.infrastructure.projections.in_memory_upstream_fact_projection_store import (
    InMemoryUpstreamFactProjectionStore,
)


TENANT = "tn_test01"
REG_SOURCE = "urn:baobab-platform:service:baobab-regulations"
DOC_SOURCE = "urn:baobab-platform:service:baobab-trade-docs"


def _ref(owner: str, object_type: str, object_id: str) -> dict[str, str]:
    return {
        "owner_engine_id": owner,
        "object_type": object_type,
        "object_id": object_id,
        "reference_mode": "IDENTITY_PINNED",
        "scope": "tenant",
        "tenant_id": TENANT,
    }


def _event(
    *,
    event_type: str,
    source: str,
    data: dict[str, object],
    event_id: UUID | None = None,
    tenant_id: str = TENANT,
) -> UpstreamEventEnvelope:
    return UpstreamEventEnvelope(
        id=event_id or uuid4(),
        type=event_type,
        source=source,
        subject="subject:1",
        time="2026-10-06T12:00:00Z",
        dataschema="https://contracts.baobab-platform.com/example.schema.json",
        baobabscope="tenant",
        correlationid=uuid4(),
        tenantid=tenant_id,
        data=data,
    )


async def test_document_verification_is_projected_as_documentary_fact_not_regulatory_satisfaction() -> None:
    store = InMemoryUpstreamFactProjectionStore()
    service = UpstreamFactProjectionService(projection_port=store)
    event = _event(
        event_type=DOCUMENTS_VERIFICATION,
        source=DOC_SOURCE,
        data={
            "trade_document_id": "tdoc_01",
            "document_version_id": "tdocv_01",
            "tenant_id": TENANT,
            "previous_verification_state": "PENDING",
            "verification_state": "VERIFIED",
            "reason_code": "SIGNATURE_VERIFIED",
            "changed_at": "2026-10-06T12:00:00Z",
        },
    )

    result = await service.consume(event)

    assert result.created is True
    assert result.projection.fact_kind == UpstreamFactKind.DOCUMENT_VERIFICATION_CHANGED
    assert result.projection.state_code == "VERIFIED"
    assert all(reference.owner_engine_id == "baobab-trade-docs" for reference in result.projection.references)
    assert "SATISFIED" not in (result.projection.state_code or "")


async def test_same_upstream_occurrence_is_idempotent_but_conflicting_replay_fails_closed() -> None:
    store = InMemoryUpstreamFactProjectionStore()
    service = UpstreamFactProjectionService(projection_port=store)
    event_id = uuid4()
    data = {
        "trade_document_id": "tdoc_01",
        "document_version_id": "tdocv_01",
        "tenant_id": TENANT,
        "verification_state": "VERIFIED",
        "changed_at": "2026-10-06T12:00:00Z",
    }

    event = _event(event_type=DOCUMENTS_VERIFICATION, source=DOC_SOURCE, data=data, event_id=event_id)
    first = await service.consume(event)
    second = await service.consume(event)

    assert first.created is True
    assert second.created is False

    conflicting = _event(
        event_type=DOCUMENTS_VERIFICATION,
        source=DOC_SOURCE,
        data={**data, "verification_state": "FAILED"},
        event_id=event_id,
    )
    with pytest.raises(InvariantViolation, match="conflicting payload digest"):
        await service.consume(conflicting)


async def test_wrong_logical_producer_is_rejected() -> None:
    service = UpstreamFactProjectionService(projection_port=InMemoryUpstreamFactProjectionStore())
    event = _event(
        event_type=DOCUMENTS_VERIFICATION,
        source=REG_SOURCE,
        data={
            "trade_document_id": "tdoc_01",
            "document_version_id": "tdocv_01",
            "tenant_id": TENANT,
            "verification_state": "VERIFIED",
            "changed_at": "2026-10-06T12:00:00Z",
        },
    )

    with pytest.raises(InvariantViolation, match="must come from"):
        await service.consume(event)


async def test_envelope_and_payload_tenant_must_match() -> None:
    service = UpstreamFactProjectionService(projection_port=InMemoryUpstreamFactProjectionStore())
    event = _event(
        event_type=DOCUMENTS_VERIFICATION,
        source=DOC_SOURCE,
        tenant_id="tn_other01",
        data={
            "trade_document_id": "tdoc_01",
            "document_version_id": "tdocv_01",
            "tenant_id": TENANT,
            "verification_state": "VERIFIED",
            "changed_at": "2026-10-06T12:00:00Z",
        },
    )

    with pytest.raises(InvariantViolation, match="differs from payload tenant"):
        await service.consume(event)


async def test_regulations_satisfaction_projection_retains_owner_references() -> None:
    service = UpstreamFactProjectionService(projection_port=InMemoryUpstreamFactProjectionStore())
    event = _event(
        event_type=REGULATIONS_SATISFACTION,
        source=REG_SOURCE,
        data={
            "tenant_id": TENANT,
            "result": {
                "assessment_reference": _ref(
                    "baobab-regulations", "REGULATORY_EVIDENCE_ASSESSMENT", "regassess_01"
                ),
                "regulatory_decision_reference": _ref(
                    "baobab-regulations", "REGULATORY_DECISION", "regdec_01"
                ),
                "requirement_reference": _ref(
                    "baobab-regulations", "DOCUMENT_REQUIREMENT", "regreq_01"
                ),
                "outcome": "SATISFIED",
                "accepted_document_version_references": [
                    _ref("baobab-trade-docs", "DOCUMENT_VERSION", "tdocv_01")
                ],
                "rejected_evidence": [],
                "reason_codes": ["DOCUMENT_ACCEPTED"],
                "resulting_regulatory_decision_reference": None,
                "evaluated_at": "2026-10-06T12:00:00Z",
            },
        },
    )

    result = await service.consume(event)

    assert result.projection.fact_kind == UpstreamFactKind.REQUIREMENT_SATISFACTION_EVALUATED
    assert result.projection.state_code == "SATISFIED"
    owners = {reference.owner_engine_id for reference in result.projection.references}
    assert owners == {"baobab-regulations", "baobab-trade-docs"}

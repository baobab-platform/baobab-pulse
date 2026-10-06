"""RTD-09 consumer: project authoritative upstream facts into Pulse read models.

The service is intentionally one-way and asynchronous. It does not call
Regulations or Trade Docs and cannot participate in regulatory/documentary
enforcement. It validates canonical producer/type/tenant/reference semantics,
then persists only a minimal, rebuildable analytical projection.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from baobab_pulse.application.ports.upstream_fact_projection_port import UpstreamFactProjectionPort
from baobab_pulse.contracts.upstream_events import (
    DocumentRequirementsDeterminedData,
    DocumentVersionValidityChangedData,
    DocumentVersionVerificationChangedData,
    RegulatoryEvidenceOfferedData,
    RequirementSatisfactionEvaluatedData,
    UpstreamEventEnvelope,
)
from baobab_pulse.domain.projections import UpstreamFactKind, UpstreamFactProjection
from baobab_pulse.domain.shared.errors import InvariantViolation
from baobab_pulse.domain.shared.value_objects import (
    CrossEngineObjectReference,
    CrossEngineReferenceMode,
    CrossEngineReferenceScope,
)

_REGULATIONS_SOURCE = "urn:baobab-platform:service:baobab-regulations"
_TRADE_DOCS_SOURCE = "urn:baobab-platform:service:baobab-trade-docs"

REGULATIONS_REQUIREMENTS = "com.baobab-platform.regulations.document-requirements.determined.v1"
REGULATIONS_SATISFACTION = "com.baobab-platform.regulations.requirement-satisfaction.evaluated.v1"
DOCUMENTS_EVIDENCE_OFFERED = "com.baobab-platform.documents.regulatory-evidence.offered.v1"
DOCUMENTS_VERIFICATION = "com.baobab-platform.documents.document-version.verification-changed.v2"
DOCUMENTS_VALIDITY = "com.baobab-platform.documents.document-version.validity-changed.v2"

_SUPPORTED_SOURCES = {
    REGULATIONS_REQUIREMENTS: (_REGULATIONS_SOURCE, "baobab-regulations"),
    REGULATIONS_SATISFACTION: (_REGULATIONS_SOURCE, "baobab-regulations"),
    DOCUMENTS_EVIDENCE_OFFERED: (_TRADE_DOCS_SOURCE, "baobab-trade-docs"),
    DOCUMENTS_VERIFICATION: (_TRADE_DOCS_SOURCE, "baobab-trade-docs"),
    DOCUMENTS_VALIDITY: (_TRADE_DOCS_SOURCE, "baobab-trade-docs"),
}

_ModelT = TypeVar("_ModelT", bound=BaseModel)


@dataclass(frozen=True)
class ProjectionIngestResult:
    projection: UpstreamFactProjection
    created: bool


class UpstreamFactProjectionService:
    """Validate and project one supported upstream event."""

    def __init__(self, *, projection_port: UpstreamFactProjectionPort) -> None:
        self._projection_port = projection_port

    async def consume(self, event: UpstreamEventEnvelope) -> ProjectionIngestResult:
        source_binding = _SUPPORTED_SOURCES.get(event.type)
        if source_binding is None:
            raise InvariantViolation(f"unsupported RTD-09 upstream event type: {event.type}")

        expected_source, source_engine_id = source_binding
        if event.source != expected_source:
            raise InvariantViolation(
                f"{event.type} must come from {expected_source}, got {event.source}"
            )
        if event.baobabscope != "tenant" or event.tenantid is None:
            raise InvariantViolation("RTD-09 upstream regulatory/document events must be tenant-scoped")

        if event.type == REGULATIONS_REQUIREMENTS:
            projection = self._requirements_projection(event, source_engine_id)
        elif event.type == REGULATIONS_SATISFACTION:
            projection = self._satisfaction_projection(event, source_engine_id)
        elif event.type == DOCUMENTS_EVIDENCE_OFFERED:
            projection = self._evidence_offered_projection(event, source_engine_id)
        elif event.type == DOCUMENTS_VERIFICATION:
            projection = self._verification_projection(event, source_engine_id)
        elif event.type == DOCUMENTS_VALIDITY:
            projection = self._validity_projection(event, source_engine_id)
        else:  # pragma: no cover - protected by _SUPPORTED_SOURCES
            raise InvariantViolation(f"unhandled RTD-09 event type: {event.type}")

        created = await self._projection_port.put_if_absent(projection)
        return ProjectionIngestResult(projection=projection, created=created)

    def _requirements_projection(
        self, event: UpstreamEventEnvelope, source_engine_id: str
    ) -> UpstreamFactProjection:
        data = self._parse(DocumentRequirementsDeterminedData, event.data)
        self._assert_event_tenant(event, data.tenant_id)
        decision = data.requirement_set.regulatory_decision_reference
        self._expect_reference(
            decision,
            owner="baobab-regulations",
            object_types={"REGULATORY_DECISION"},
            tenant_id=data.tenant_id,
            pinned=True,
        )
        references: list[CrossEngineObjectReference] = [decision]
        for item in data.requirement_set.requirements:
            self._expect_reference(
                item.regulatory_decision_reference,
                owner="baobab-regulations",
                object_types={"REGULATORY_DECISION"},
                tenant_id=data.tenant_id,
                pinned=True,
            )
            if item.regulatory_decision_reference != decision:
                raise InvariantViolation("requirement projection decision reference disagrees with requirement set")
            self._expect_reference(
                item.requirement_reference,
                owner="baobab-regulations",
                object_types={"DOCUMENT_REQUIREMENT", "PERMIT_REQUIREMENT", "EVIDENCE_REQUIREMENT"},
                tenant_id=data.tenant_id,
                pinned=True,
            )
            references.append(item.requirement_reference)

        return self._projection(
            event,
            source_engine_id=source_engine_id,
            tenant_id=data.tenant_id,
            kind=UpstreamFactKind.DOCUMENT_REQUIREMENTS_DETERMINED,
            references=tuple(references),
            state_code="DETERMINED",
        )

    def _satisfaction_projection(
        self, event: UpstreamEventEnvelope, source_engine_id: str
    ) -> UpstreamFactProjection:
        data = self._parse(RequirementSatisfactionEvaluatedData, event.data)
        self._assert_event_tenant(event, data.tenant_id)
        result = data.result

        self._expect_reference(
            result.assessment_reference,
            owner="baobab-regulations",
            object_types={"REGULATORY_EVIDENCE_ASSESSMENT"},
            tenant_id=data.tenant_id,
            pinned=True,
        )
        self._expect_reference(
            result.regulatory_decision_reference,
            owner="baobab-regulations",
            object_types={"REGULATORY_DECISION"},
            tenant_id=data.tenant_id,
            pinned=True,
        )
        self._expect_reference(
            result.requirement_reference,
            owner="baobab-regulations",
            object_types={"DOCUMENT_REQUIREMENT", "PERMIT_REQUIREMENT", "EVIDENCE_REQUIREMENT"},
            tenant_id=data.tenant_id,
            pinned=True,
        )

        references: list[CrossEngineObjectReference] = [
            result.assessment_reference,
            result.regulatory_decision_reference,
            result.requirement_reference,
        ]
        for reference in result.accepted_document_version_references:
            self._expect_document_version(reference, data.tenant_id)
            references.append(reference)
        for rejected in result.rejected_evidence:
            self._expect_document_version(rejected.document_version_reference, data.tenant_id)
            references.append(rejected.document_version_reference)
        if result.resulting_regulatory_decision_reference is not None:
            self._expect_reference(
                result.resulting_regulatory_decision_reference,
                owner="baobab-regulations",
                object_types={"REGULATORY_DECISION"},
                tenant_id=data.tenant_id,
                pinned=True,
            )
            references.append(result.resulting_regulatory_decision_reference)

        return self._projection(
            event,
            source_engine_id=source_engine_id,
            tenant_id=data.tenant_id,
            kind=UpstreamFactKind.REQUIREMENT_SATISFACTION_EVALUATED,
            references=tuple(references),
            state_code=result.outcome,
        )

    def _evidence_offered_projection(
        self, event: UpstreamEventEnvelope, source_engine_id: str
    ) -> UpstreamFactProjection:
        data = self._parse(RegulatoryEvidenceOfferedData, event.data)
        self._assert_event_tenant(event, data.tenant_id)
        self._expect_reference(
            data.regulatory_decision_reference,
            owner="baobab-regulations",
            object_types={"REGULATORY_DECISION"},
            tenant_id=data.tenant_id,
            pinned=True,
        )
        self._expect_reference(
            data.requirement_reference,
            owner="baobab-regulations",
            object_types={"DOCUMENT_REQUIREMENT", "PERMIT_REQUIREMENT", "EVIDENCE_REQUIREMENT"},
            tenant_id=data.tenant_id,
            pinned=True,
        )
        for reference in data.document_version_references:
            self._expect_document_version(reference, data.tenant_id)

        references = (
            data.regulatory_decision_reference,
            data.requirement_reference,
            *data.document_version_references,
        )
        return self._projection(
            event,
            source_engine_id=source_engine_id,
            tenant_id=data.tenant_id,
            kind=UpstreamFactKind.REGULATORY_EVIDENCE_OFFERED,
            references=references,
            state_code="OFFERED",
        )

    def _verification_projection(
        self, event: UpstreamEventEnvelope, source_engine_id: str
    ) -> UpstreamFactProjection:
        data = self._parse(DocumentVersionVerificationChangedData, event.data)
        self._assert_event_tenant(event, data.tenant_id)
        reference = self._document_version_reference(data.document_version_id, data.tenant_id)
        return self._projection(
            event,
            source_engine_id=source_engine_id,
            tenant_id=data.tenant_id,
            kind=UpstreamFactKind.DOCUMENT_VERIFICATION_CHANGED,
            references=(reference,),
            state_code=data.verification_state,
        )

    def _validity_projection(
        self, event: UpstreamEventEnvelope, source_engine_id: str
    ) -> UpstreamFactProjection:
        data = self._parse(DocumentVersionValidityChangedData, event.data)
        self._assert_event_tenant(event, data.tenant_id)
        reference = self._document_version_reference(data.document_version_id, data.tenant_id)
        return self._projection(
            event,
            source_engine_id=source_engine_id,
            tenant_id=data.tenant_id,
            kind=UpstreamFactKind.DOCUMENT_VALIDITY_CHANGED,
            references=(reference,),
            state_code=data.temporal_validity_state,
        )

    def _projection(
        self,
        event: UpstreamEventEnvelope,
        *,
        source_engine_id: str,
        tenant_id: str,
        kind: UpstreamFactKind,
        references: tuple[CrossEngineObjectReference, ...],
        state_code: str | None,
    ) -> UpstreamFactProjection:
        return UpstreamFactProjection(
            source_event_id=event.id,
            source_event_source=event.source,
            source_event_type=event.type,
            source_engine_id=source_engine_id,
            tenant_id=tenant_id,
            occurred_at=event.time,
            correlation_id=event.correlationid,
            fact_kind=kind,
            references=references,
            state_code=state_code,
            event_digest=self._event_digest(event),
        )

    @staticmethod
    def _parse(model: type[_ModelT], data: dict[str, Any]) -> _ModelT:
        try:
            return model.model_validate(data)
        except ValidationError as exc:
            raise InvariantViolation(f"upstream event payload violates expected Shared contract: {exc}") from exc

    @staticmethod
    def _event_digest(event: UpstreamEventEnvelope) -> str:
        """Digest the immutable canonical occurrence, not only event.data.

        Shared defines (source, id) as the delivery identity. Reusing that
        identity with a changed type, subject, tenant, occurrence time or
        payload is therefore a provenance conflict and must fail closed.
        """
        canonical = json.dumps(
            event.model_dump(mode="json", exclude_none=True),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _assert_event_tenant(event: UpstreamEventEnvelope, payload_tenant: str) -> None:
        if event.tenantid != payload_tenant:
            raise InvariantViolation(
                f"event tenant {event.tenantid!r} differs from payload tenant {payload_tenant!r}"
            )

    @staticmethod
    def _document_version_reference(object_id: str, tenant_id: str) -> CrossEngineObjectReference:
        return CrossEngineObjectReference(
            owner_engine_id="baobab-trade-docs",
            object_type="DOCUMENT_VERSION",
            object_id=object_id,
            reference_mode=CrossEngineReferenceMode.IDENTITY_PINNED,
            scope=CrossEngineReferenceScope.TENANT,
            tenant_id=tenant_id,
        )

    def _expect_document_version(self, reference: CrossEngineObjectReference, tenant_id: str) -> None:
        self._expect_reference(
            reference,
            owner="baobab-trade-docs",
            object_types={"DOCUMENT_VERSION"},
            tenant_id=tenant_id,
            pinned=True,
        )
        if reference.reference_mode != CrossEngineReferenceMode.IDENTITY_PINNED:
            raise InvariantViolation("Trade Docs DocumentVersion evidence must be IDENTITY_PINNED")

    @staticmethod
    def _expect_reference(
        reference: CrossEngineObjectReference,
        *,
        owner: str,
        object_types: set[str],
        tenant_id: str,
        pinned: bool,
    ) -> None:
        if reference.owner_engine_id != owner:
            raise InvariantViolation(
                f"expected reference owner {owner}, got {reference.owner_engine_id}"
            )
        if reference.object_type not in object_types:
            raise InvariantViolation(
                f"unexpected {owner} object type {reference.object_type}; expected {sorted(object_types)}"
            )
        if reference.scope != CrossEngineReferenceScope.TENANT or reference.tenant_id != tenant_id:
            raise InvariantViolation("cross-engine reference tenant does not match upstream event tenant")
        if pinned and reference.reference_mode == CrossEngineReferenceMode.CURRENT:
            raise InvariantViolation("consequential upstream reference must be historically pinned")

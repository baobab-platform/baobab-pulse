"""Consumer-side wire models for RTD-09 upstream facts.

Shared remains the contract authority. These Pydantic types form a strict
anti-corruption layer for the exact ACTIVE Regulations/Trade Docs facts Pulse
consumes. They deliberately mirror the relevant Shared constraints rather
than redefining upstream ownership.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from baobab_pulse.contracts.events import PulseEventEnvelope
from baobab_pulse.domain.shared.value_objects import CrossEngineObjectReference

TenantId = Annotated[str, Field(pattern=r"^tn_[a-z0-9]+$", min_length=6, max_length=63)]
TradeDocumentId = Annotated[str, Field(pattern=r"^tdoc_[a-z0-9]+$", min_length=8, max_length=63)]
DocumentVersionId = Annotated[str, Field(pattern=r"^tdocv_[a-z0-9]+$", min_length=9, max_length=63)]
ReasonCode = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{2,127}$")]
DocumentTypeCode = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{1,63}$")]
IssuerRole = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{1,63}$")]
DataElementCode = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_.-]{1,127}$")]
VerificationState = Literal["UNVERIFIED", "PENDING", "VERIFIED", "FAILED", "DISPUTED", "UNKNOWN"]
TemporalValidityState = Literal["NOT_YET_EFFECTIVE", "CURRENTLY_VALID", "EXPIRED", "REVOKED", "UNKNOWN"]
RequirementKind = Literal["DOCUMENT", "PERMIT", "EVIDENCE"]
SatisfactionOutcome = Literal["SATISFIED", "UNSATISFIED", "INDETERMINATE", "NOT_APPLICABLE", "REVIEW_REQUIRED"]


def _assert_unique(values: tuple[object, ...], field_name: str) -> None:
    fingerprints = [
        value.model_dump_json(exclude_none=True) if isinstance(value, BaseModel) else repr(value)
        for value in values
    ]
    if len(set(fingerprints)) != len(fingerprints):
        raise ValueError(f"{field_name} must contain unique items")


class UpstreamEventEnvelope(PulseEventEnvelope):
    """Canonical Shared CloudEvents envelope received from another engine."""


class _StrictPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DocumentVersionVerificationChangedData(_StrictPayload):
    trade_document_id: TradeDocumentId
    document_version_id: DocumentVersionId
    tenant_id: TenantId
    previous_verification_state: VerificationState | None = None
    verification_state: VerificationState
    reason_code: ReasonCode | None = None
    changed_at: datetime


class DocumentVersionValidityChangedData(_StrictPayload):
    trade_document_id: TradeDocumentId
    document_version_id: DocumentVersionId
    tenant_id: TenantId
    previous_temporal_validity_state: TemporalValidityState | None = None
    temporal_validity_state: TemporalValidityState
    authority_reference: Annotated[str, Field(max_length=256)] | None = None
    basis_reference: Annotated[str, Field(max_length=512)] | None = None
    changed_at: datetime


class RegulatoryEvidenceOfferedData(_StrictPayload):
    tenant_id: TenantId
    regulatory_decision_reference: CrossEngineObjectReference
    requirement_reference: CrossEngineObjectReference
    document_version_references: Annotated[
        tuple[CrossEngineObjectReference, ...], Field(min_length=1, max_length=50)
    ]
    offered_at: datetime

    @model_validator(mode="after")
    def _unique_document_versions(self) -> RegulatoryEvidenceOfferedData:
        _assert_unique(self.document_version_references, "document_version_references")
        return self


class RegulatoryRequirementProjection(_StrictPayload):
    requirement_reference: CrossEngineObjectReference
    regulatory_decision_reference: CrossEngineObjectReference
    requirement_kind: RequirementKind
    requirement_code: ReasonCode
    purpose_code: ReasonCode
    acceptable_document_types: Annotated[tuple[DocumentTypeCode, ...], Field(max_length=64)]
    required_issuer_roles: Annotated[tuple[IssuerRole, ...], Field(max_length=32)]
    required_data_elements: Annotated[tuple[DataElementCode, ...], Field(max_length=128)]
    unsatisfied_effect_code: ReasonCode
    effective_from: datetime
    effective_to: datetime | None = None
    determined_at: datetime

    @model_validator(mode="after")
    def _unique_requirement_lists(self) -> RegulatoryRequirementProjection:
        _assert_unique(self.acceptable_document_types, "acceptable_document_types")
        _assert_unique(self.required_issuer_roles, "required_issuer_roles")
        _assert_unique(self.required_data_elements, "required_data_elements")
        return self


class RegulatoryDocumentRequirementSet(_StrictPayload):
    regulatory_decision_reference: CrossEngineObjectReference
    requirements: Annotated[tuple[RegulatoryRequirementProjection, ...], Field(max_length=200)]
    legal_time: datetime
    knowledge_time: datetime
    determined_at: datetime


class DocumentRequirementsDeterminedData(_StrictPayload):
    tenant_id: TenantId
    requirement_set: RegulatoryDocumentRequirementSet


class RejectedEvidenceProjection(_StrictPayload):
    document_version_reference: CrossEngineObjectReference
    reason_codes: Annotated[tuple[ReasonCode, ...], Field(min_length=1, max_length=32)]

    @model_validator(mode="after")
    def _unique_reason_codes(self) -> RejectedEvidenceProjection:
        _assert_unique(self.reason_codes, "reason_codes")
        return self


class DocumentEvidenceAssessmentResult(_StrictPayload):
    assessment_reference: CrossEngineObjectReference
    regulatory_decision_reference: CrossEngineObjectReference
    requirement_reference: CrossEngineObjectReference
    outcome: SatisfactionOutcome
    accepted_document_version_references: Annotated[
        tuple[CrossEngineObjectReference, ...], Field(max_length=50)
    ]
    rejected_evidence: Annotated[tuple[RejectedEvidenceProjection, ...], Field(max_length=50)]
    reason_codes: Annotated[tuple[ReasonCode, ...], Field(max_length=64)]
    resulting_regulatory_decision_reference: CrossEngineObjectReference | None = None
    evaluated_at: datetime

    @model_validator(mode="after")
    def _unique_assessment_lists(self) -> DocumentEvidenceAssessmentResult:
        _assert_unique(self.accepted_document_version_references, "accepted_document_version_references")
        _assert_unique(self.reason_codes, "reason_codes")
        return self


class RequirementSatisfactionEvaluatedData(_StrictPayload):
    tenant_id: TenantId
    result: DocumentEvidenceAssessmentResult

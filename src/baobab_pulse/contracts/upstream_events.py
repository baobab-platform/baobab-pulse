"""Consumer-side wire models for RTD-09 upstream facts.

Shared remains the contract authority. These Pydantic types are an
anti-corruption layer used to project the exact ACTIVE Regulations/Trade Docs
facts needed by Pulse; they do not redefine upstream ownership.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from baobab_pulse.contracts.events import PulseEventEnvelope
from baobab_pulse.domain.shared.value_objects import CrossEngineObjectReference


class UpstreamEventEnvelope(PulseEventEnvelope):
    """Canonical Shared CloudEvents envelope received from another engine."""


class _StrictPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DocumentVersionVerificationChangedData(_StrictPayload):
    trade_document_id: str
    document_version_id: str
    tenant_id: str
    previous_verification_state: str | None = None
    verification_state: Literal["UNVERIFIED", "PENDING", "VERIFIED", "FAILED", "DISPUTED", "UNKNOWN"]
    reason_code: str | None = None
    changed_at: datetime


class DocumentVersionValidityChangedData(_StrictPayload):
    trade_document_id: str
    document_version_id: str
    tenant_id: str
    previous_temporal_validity_state: str | None = None
    temporal_validity_state: Literal["NOT_YET_EFFECTIVE", "CURRENTLY_VALID", "EXPIRED", "REVOKED", "UNKNOWN"]
    authority_reference: str | None = None
    basis_reference: str | None = None
    changed_at: datetime


class RegulatoryEvidenceOfferedData(_StrictPayload):
    tenant_id: str
    regulatory_decision_reference: CrossEngineObjectReference
    requirement_reference: CrossEngineObjectReference
    document_version_references: tuple[CrossEngineObjectReference, ...]
    offered_at: datetime


class RegulatoryRequirementProjection(_StrictPayload):
    requirement_reference: CrossEngineObjectReference
    regulatory_decision_reference: CrossEngineObjectReference
    requirement_kind: Literal["DOCUMENT", "PERMIT", "EVIDENCE"]
    requirement_code: str
    purpose_code: str
    acceptable_document_types: tuple[str, ...]
    required_issuer_roles: tuple[str, ...]
    required_data_elements: tuple[str, ...]
    unsatisfied_effect_code: str
    effective_from: datetime
    effective_to: datetime | None = None
    determined_at: datetime


class RegulatoryDocumentRequirementSet(_StrictPayload):
    regulatory_decision_reference: CrossEngineObjectReference
    requirements: tuple[RegulatoryRequirementProjection, ...]
    legal_time: datetime
    knowledge_time: datetime
    determined_at: datetime


class DocumentRequirementsDeterminedData(_StrictPayload):
    tenant_id: str
    requirement_set: RegulatoryDocumentRequirementSet


class RejectedEvidenceProjection(_StrictPayload):
    document_version_reference: CrossEngineObjectReference
    reason_codes: tuple[str, ...]


class DocumentEvidenceAssessmentResult(_StrictPayload):
    assessment_reference: CrossEngineObjectReference
    regulatory_decision_reference: CrossEngineObjectReference
    requirement_reference: CrossEngineObjectReference
    outcome: Literal["SATISFIED", "UNSATISFIED", "INDETERMINATE", "NOT_APPLICABLE", "REVIEW_REQUIRED"]
    accepted_document_version_references: tuple[CrossEngineObjectReference, ...]
    rejected_evidence: tuple[RejectedEvidenceProjection, ...]
    reason_codes: tuple[str, ...]
    resulting_regulatory_decision_reference: CrossEngineObjectReference | None = None
    evaluated_at: datetime


class RequirementSatisfactionEvaluatedData(_StrictPayload):
    tenant_id: str
    result: DocumentEvidenceAssessmentResult

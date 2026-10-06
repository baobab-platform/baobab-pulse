"""Canonical value objects shared across every Pulse aggregate.

Source: ARCH-PULSE-CIM-001 §130 ("Canonical value objects... implement once
and reuse"), with individual field lists drawn from §5 (context), §36-37
(quality/confidence), §86 (temporal), §131-132 (Money/Quantity), and
ADR-PULSE-007 (temporal semantics) / ADR-PULSE-009 (quality).

All value objects are frozen (immutable) — a value object is replaced, never
mutated in place.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from baobab_pulse.domain.shared.enums import ActorType, ConfidenceBand, ConfidenceMethod, TransformationType


class ValueObject(BaseModel):
    """Base for every frozen Pulse value object."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class TemporalContext(ValueObject):
    """ADR-PULSE-007 §6 / ARCH-PULSE-CIM-001 §86.

    "No generic ``date`` field SHALL replace these semantics" (CIM §86).
    Only ``valid_time`` is required — every other dimension is populated
    when the producing context actually knows it; absence is not the same
    as "now".
    """

    valid_time: datetime
    observed_time: datetime | None = None
    event_time: datetime | None = None
    published_time: datetime | None = None
    announced_time: datetime | None = None
    effective_time: datetime | None = None
    retrieved_time: datetime | None = None
    processed_time: datetime | None = None
    recorded_time: datetime | None = None
    created_time: datetime | None = None
    superseded_time: datetime | None = None


class TenantContext(ValueObject):
    """ARCH-PULSE-CIM-001 §5 (Canonical Context fields, tenancy subset).

    ``tenant_id`` is the Control-Plane-minted tenant identity (ADR-PULSE-001
    INV-PULSE-004: Pulse SHALL NOT redefine Control Plane canonical
    identities — this field is a reference, never a locally-issued tenant
    record).
    """

    tenant_id: str
    context_id: str | None = None
    organisation_id: str | None = None
    legal_entity_id: str | None = None
    digital_estate_id: str | None = None


class GeographicContext(ValueObject):
    """ARCH-PULSE-CIM-001 §5 / §85 (Location hierarchy)."""

    country_id: str | None = None
    region_id: str | None = None
    location_id: str | None = None


class MarketContext(ValueObject):
    """ARCH-PULSE-CIM-001 §5 / §84 (Market — reuses Control Plane ``Market``;
    Pulse never defines independent market semantics)."""

    market_id: str | None = None


class Money(ValueObject):
    """ARCH-PULSE-CIM-001 §131: "a naked decimal SHALL NOT represent
    monetary value" — amount and currency always travel together."""

    amount: float
    currency: str

    @model_validator(mode="after")
    def _currency_shape(self) -> Money:
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError(f"currency must be a 3-letter ISO 4217 code, got {self.currency!r}")
        return self


class Quantity(ValueObject):
    """ARCH-PULSE-CIM-001 §132: value and unit always travel together."""

    value: float
    unit: str


class Reference(ValueObject):
    """Pulse-local typed pointer.

    Cross-engine wire identity uses :class:`CrossEngineObjectReference`
    (ADR-SHARED-021 / RTD-05). This older value object remains valid for
    references whose ownership is entirely inside Pulse.
    """

    object_type: str
    object_id: str
    version: str | None = None


class CrossEngineReferenceMode(StrEnum):
    """ADR-SHARED-021 reference-resolution semantics."""

    CURRENT = "CURRENT"
    IDENTITY_PINNED = "IDENTITY_PINNED"
    VERSION_PINNED = "VERSION_PINNED"


class CrossEngineReferenceScope(StrEnum):
    PLATFORM = "platform"
    TENANT = "tenant"


class CrossEngineVersionKind(StrEnum):
    VERSION = "VERSION"
    REVISION = "REVISION"
    SEQUENCE = "SEQUENCE"
    ETAG = "ETAG"
    CONTENT_HASH = "CONTENT_HASH"
    OTHER = "OTHER"


class CrossEngineObjectVersion(ValueObject):
    """Opaque owner-defined historical version/revision."""

    kind: CrossEngineVersionKind
    value: str

    @model_validator(mode="after")
    def _value_shape(self) -> CrossEngineObjectVersion:
        if not (1 <= len(self.value) <= 256):
            raise ValueError("cross-engine object version value must be 1..256 characters")
        return self


_ENGINE_ID = re.compile(r"^baobab-[a-z][a-z0-9-]*$")
_OBJECT_TYPE = re.compile(r"^[A-Z][A-Z0-9_]{1,95}$")
_OBJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_TENANT_ID = re.compile(r"^tn_[a-z0-9]+$")


class CrossEngineObjectReference(ValueObject):
    """Portable owner-preserving reference from ADR-SHARED-021.

    The reference carries identity and historical pinning only. It never
    embeds the foreign aggregate and never grants access to it.
    """

    owner_engine_id: str
    object_type: str
    object_id: str
    reference_mode: CrossEngineReferenceMode
    scope: CrossEngineReferenceScope
    tenant_id: str | None = None
    object_version: CrossEngineObjectVersion | None = None

    @model_validator(mode="after")
    def _shared_contract_invariants(self) -> CrossEngineObjectReference:
        if not _ENGINE_ID.fullmatch(self.owner_engine_id):
            raise ValueError("owner_engine_id must use the canonical baobab-<engine> grammar")
        if not _OBJECT_TYPE.fullmatch(self.object_type):
            raise ValueError("object_type must use the canonical uppercase semantic-code grammar")
        if not (1 <= len(self.object_id) <= 160) or not _OBJECT_ID.fullmatch(self.object_id):
            raise ValueError("object_id does not satisfy the Shared cross-engine reference grammar")

        if self.scope == CrossEngineReferenceScope.TENANT:
            if self.tenant_id is None or not _TENANT_ID.fullmatch(self.tenant_id):
                raise ValueError("tenant-scoped references require a canonical tenant_id")
        elif self.tenant_id is not None:
            raise ValueError("platform-scoped references must not carry tenant_id")

        if self.reference_mode == CrossEngineReferenceMode.VERSION_PINNED:
            if self.object_version is None:
                raise ValueError("VERSION_PINNED references require object_version")
        elif self.object_version is not None:
            raise ValueError("CURRENT/IDENTITY_PINNED references must not carry object_version")

        return self


class CrossEngineReferenceObservation(ValueObject):
    """Consumer-side observation metadata kept outside reference identity."""

    reference: CrossEngineObjectReference
    observed_at: datetime
    resolved_at: datetime | None = None


class QualityProfile(ValueObject):
    """ADR-PULSE-009 §10. Dimensions are ordinal (§12), never a bare
    arithmetic score, unless a defensible calibrated methodology says
    otherwise (QUAL-PULSE-006)."""

    accuracy: ConfidenceBand = ConfidenceBand.UNKNOWN
    completeness: ConfidenceBand = ConfidenceBand.UNKNOWN
    timeliness: ConfidenceBand = ConfidenceBand.UNKNOWN
    consistency: ConfidenceBand = ConfidenceBand.UNKNOWN
    authority: ConfidenceBand = ConfidenceBand.UNKNOWN
    corroboration: ConfidenceBand = ConfidenceBand.UNKNOWN
    methodology_quality: ConfidenceBand = ConfidenceBand.UNKNOWN
    representativeness: ConfidenceBand = ConfidenceBand.UNKNOWN
    precision: ConfidenceBand = ConfidenceBand.UNKNOWN
    traceability: ConfidenceBand = ConfidenceBand.UNKNOWN
    overall_assessment: ConfidenceBand = ConfidenceBand.UNKNOWN


class Confidence(ValueObject):
    """ARCH-PULSE-CIM-001 §37.

    QUAL-PULSE-021: "LLM self-reported confidence SHALL NOT be accepted as
    intelligence confidence." QUAL-PULSE-007: probability SHALL remain
    distinct from confidence — a model's ``P(x)=0.68`` is never
    ``confidence_score=68``. This type has no constructor path that accepts
    a bare float without a method and version attached.
    """

    confidence_band: ConfidenceBand
    confidence_method: ConfidenceMethod
    confidence_version: str
    confidence_score: float | None = None

    @model_validator(mode="after")
    def _score_range(self) -> Confidence:
        if self.confidence_score is not None and not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError("confidence_score must be within [0.0, 1.0] when provided")
        return self


class Provenance(ValueObject):
    """ARCH-PULSE-CIM-001 §29 (``ProvenanceRecord``).

    Records one derivation step (input -> transformation -> output). A full
    provenance *chain* is a sequence of these, traversed per CIM §30:
    Recommendation -> Insight -> Analysis -> Evidence -> Observation ->
    RawRecord -> Acquisition -> Dataset -> DataSource -> Source.
    """

    input_reference: Reference | None = None
    output_reference: Reference | None = None
    transformation_type: TransformationType
    transformation_version: str
    actor_type: ActorType
    actor_reference: str | None = None
    executed_at: datetime
    metadata: dict[str, Any] = {}

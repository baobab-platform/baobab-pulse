"""Derived upstream-fact projections for RTD-09.

These are intentionally *not* canonical copies of Regulations or Trade Docs
aggregates. They retain event provenance and owner-preserving references while
carrying only the minimum analytical state Pulse needs to build Evidence,
Analysis and downstream intelligence.

ADR-PULSE-013 / ADR-SHARED-025:
- upstream authority stays with the producing engine;
- projections are rebuildable from events;
- Pulse is not a synchronous dependency of enforcement.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import model_validator

from baobab_pulse.domain.shared.value_objects import CrossEngineObjectReference, ValueObject


class UpstreamFactKind(StrEnum):
    DOCUMENT_REQUIREMENTS_DETERMINED = "DOCUMENT_REQUIREMENTS_DETERMINED"
    REQUIREMENT_SATISFACTION_EVALUATED = "REQUIREMENT_SATISFACTION_EVALUATED"
    REGULATORY_EVIDENCE_OFFERED = "REGULATORY_EVIDENCE_OFFERED"
    DOCUMENT_VERIFICATION_CHANGED = "DOCUMENT_VERIFICATION_CHANGED"
    DOCUMENT_VALIDITY_CHANGED = "DOCUMENT_VALIDITY_CHANGED"


class UpstreamFactProjection(ValueObject):
    """Minimal, rebuildable analytical read model of one upstream event."""

    source_event_id: UUID
    source_event_source: str
    source_event_type: str
    source_engine_id: str
    tenant_id: str
    occurred_at: datetime
    correlation_id: UUID
    fact_kind: UpstreamFactKind
    references: tuple[CrossEngineObjectReference, ...]
    state_code: str | None = None
    event_digest: str

    @model_validator(mode="after")
    def _projection_invariants(self) -> UpstreamFactProjection:
        if not self.source_engine_id.startswith("baobab-"):
            raise ValueError("source_engine_id must be a Baobab engine identity")
        if not self.source_event_source.startswith("urn:baobab-platform:service:"):
            raise ValueError("source_event_source must retain the canonical logical producer URI")
        if not self.source_event_type.startswith("com.baobab-platform."):
            raise ValueError("source_event_type must be a canonical Baobab event type")
        if not self.event_digest.startswith("sha256:") or len(self.event_digest) != 71:
            raise ValueError("event_digest must be a sha256:<64-hex> digest")
        if not self.references:
            raise ValueError("an upstream fact projection must retain at least one owner reference")
        for reference in self.references:
            if reference.scope.value == "tenant" and reference.tenant_id != self.tenant_id:
                raise ValueError("tenant-scoped upstream references must match projection tenant")
        return self

    @property
    def dedupe_key(self) -> tuple[str, UUID]:
        """Canonical at-least-once delivery identity: (logical source, event id)."""

        return (self.source_event_source, self.source_event_id)

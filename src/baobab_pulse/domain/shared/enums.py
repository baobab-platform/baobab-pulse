"""Canonical enumerations shared across every Pulse aggregate.

Every member name below is quoted verbatim from the governing architecture
documents (cited per enum). Aggregate-specific enums (e.g. ``SignalType``,
``OpportunityType``) live alongside their owning aggregate instead of here.
"""

from __future__ import annotations

from enum import StrEnum


class Classification(StrEnum):
    """ARCH-PULSE-CIM-001 §97. Inheritance rule (§98): a derived object's
    classification SHALL be at least as restrictive as its most restrictive
    contributing evidence — see :func:`most_restrictive`."""

    PUBLIC = "PUBLIC"
    BAOBAB_INTERNAL = "BAOBAB_INTERNAL"
    TENANT = "TENANT"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


_CLASSIFICATION_ORDER = (
    Classification.PUBLIC,
    Classification.BAOBAB_INTERNAL,
    Classification.TENANT,
    Classification.CONFIDENTIAL,
    Classification.RESTRICTED,
)


def most_restrictive(*values: Classification) -> Classification:
    """Return the most restrictive of the given classifications (CIM §98)."""
    if not values:
        raise ValueError("at least one classification is required")
    return max(values, key=_CLASSIFICATION_ORDER.index)


class TenantScope(StrEnum):
    """ARCH-PULSE-CIM-001 §99."""

    GLOBAL = "GLOBAL"
    PLATFORM = "PLATFORM"
    TENANT = "TENANT"
    CONTEXT = "CONTEXT"
    PRIVATE = "PRIVATE"


class ConfidenceBand(StrEnum):
    """ARCH-PULSE-CIM-001 §37 / ADR-PULSE-009 §94 (the shared ordinal scale
    used for both quality dimensions and intelligence confidence — QUAL-PULSE-006
    forbids fabricating arbitrary numeric precision such as ``93.7%``)."""

    UNKNOWN = "UNKNOWN"
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class ConfidenceMethod(StrEnum):
    """ADR-PULSE-009 §96."""

    RULE_BASED = "RULE_BASED"
    STATISTICAL = "STATISTICAL"
    MODEL_CALIBRATED = "MODEL_CALIBRATED"
    EXPERT_ASSESSED = "EXPERT_ASSESSED"
    EVIDENCE_WEIGHTED = "EVIDENCE_WEIGHTED"
    HYBRID = "HYBRID"


class ActorType(StrEnum):
    """ARCH-PULSE-CIM-001 §108 (provenance actor)."""

    SYSTEM = "SYSTEM"
    HUMAN = "HUMAN"
    MODEL = "MODEL"
    EXTERNAL_SOURCE = "EXTERNAL_SOURCE"
    BAOBAB_ENGINE = "BAOBAB_ENGINE"


class TransformationType(StrEnum):
    """ARCH-PULSE-CIM-001 §106."""

    PARSE = "PARSE"
    NORMALISE = "NORMALISE"
    MAP = "MAP"
    ENRICH = "ENRICH"
    AGGREGATE = "AGGREGATE"
    FILTER = "FILTER"
    DEDUPE = "DEDUPE"
    RESOLVE = "RESOLVE"
    CLASSIFY = "CLASSIFY"
    EXTRACT = "EXTRACT"
    CALCULATE = "CALCULATE"
    MODEL = "MODEL"
    SYNTHESISE = "SYNTHESISE"


class Missingness(StrEnum):
    """ARCH-PULSE-CIM-001 §135 / ADR-PULSE-005 §17 / ADR-PULSE-009 §41.
    QUAL-PULSE-008: missing SHALL never silently become zero."""

    UNKNOWN = "UNKNOWN"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    WITHHELD = "WITHHELD"
    NOT_COLLECTED = "NOT_COLLECTED"


class EvidenceDirection(StrEnum):
    """ARCH-PULSE-CIM-001 §33 / ADR-PULSE-006 §11."""

    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    NEUTRAL = "NEUTRAL"
    CONTEXTUAL = "CONTEXTUAL"


class HistoricalRetrievalStrategy(StrEnum):
    """Qdrant refactor item 64: reserved so a future retrieval strategy can
    be added without breaking canonical data. Only ``CURRENT_ONLY`` is
    implemented today (``application.services.evidence_retrieval_service``
    always searches and hydrates the latest canonical version); the other
    members exist so a caller-facing parameter can be introduced later
    without a breaking rename."""

    CURRENT_ONLY = "CURRENT_ONLY"
    CURRENT_AND_RECENT = "CURRENT_AND_RECENT"
    ALL_REVISIONS = "ALL_REVISIONS"
    SNAPSHOT_SPECIFIC = "SNAPSHOT_SPECIFIC"


class AutomationAuthorityLevel(StrEnum):
    """ADR-PULSE-001, "Automation Authority Levels". A capability may never
    jump between levels without an explicit policy (ADR-PULSE-001)."""

    OBSERVE = "OBSERVE"
    ANALYSE = "ANALYSE"
    RECOMMEND = "RECOMMEND"
    PROPOSE = "PROPOSE"
    APPROVE_BY_POLICY = "APPROVE_BY_POLICY"
    EXECUTE = "EXECUTE"

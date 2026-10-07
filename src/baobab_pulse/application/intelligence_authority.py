"""P-CAP-07 Intelligence operation and classification authority.

Tenant authority never comes from these scopes; it remains Control Plane-owned.
"""

from baobab_pulse.application.ports.authentication import AuthenticatedCaller
from baobab_pulse.domain.shared.enums import Classification
from baobab_pulse.domain.shared.errors import CapabilityAccessDeniedError

EVIDENCE_SEARCH_SCOPE = "intelligence:evidence:search"
RESEARCH_MISSION_MANAGE_SCOPE = "intelligence:research-mission:manage"
RESTRICTED_CLEARANCE_SCOPE = "intelligence:restricted"

_CLASSIFICATION_ORDER = (
    Classification.PUBLIC,
    Classification.BAOBAB_INTERNAL,
    Classification.TENANT,
    Classification.CONFIDENTIAL,
    Classification.RESTRICTED,
)


def require_capability_scope(
    caller: AuthenticatedCaller,
    required_scope: str,
) -> None:
    """Require exact route authority; supplemental scopes never imply an operation."""

    if required_scope not in caller.scopes:
        raise CapabilityAccessDeniedError(
            "the authenticated caller lacks the required Intelligence capability scope"
        )


def classification_clearance(
    caller: AuthenticatedCaller,
    *,
    required_scope: str,
) -> Classification:
    """Derive clearance from authenticated IAM authority after exact scope check."""

    require_capability_scope(caller, required_scope)
    if RESTRICTED_CLEARANCE_SCOPE in caller.scopes:
        return Classification.RESTRICTED
    return Classification.CONFIDENTIAL


def permits_classification(
    clearance: Classification,
    classification: Classification,
) -> bool:
    return _CLASSIFICATION_ORDER.index(classification) <= _CLASSIFICATION_ORDER.index(
        clearance
    )


__all__ = [
    "EVIDENCE_SEARCH_SCOPE",
    "RESEARCH_MISSION_MANAGE_SCOPE",
    "RESTRICTED_CLEARANCE_SCOPE",
    "classification_clearance",
    "permits_classification",
    "require_capability_scope",
]

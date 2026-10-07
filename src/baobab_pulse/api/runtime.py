"""Runtime dependencies for canonical Pulse capability routes."""

from dataclasses import dataclass

from baobab_pulse.application.ports.authentication import WorkloadAuthenticatorPort
from baobab_pulse.application.services.evidence_search_capability import EvidenceSearchCapabilityService


@dataclass(frozen=True, slots=True)
class CapabilityApiRuntime:
    """Dependencies required before canonical intelligence routes can serve traffic."""

    authenticator: WorkloadAuthenticatorPort
    evidence_search: EvidenceSearchCapabilityService


__all__ = ["CapabilityApiRuntime"]

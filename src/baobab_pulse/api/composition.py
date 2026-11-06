"""P-CAP-07 production composition for canonical capability routes."""

from __future__ import annotations

import urllib.parse

from baobab_pulse.api.dependencies import (
    get_database,
    get_evidence_retrieval_service,
    get_research_mission_mutation_store,
    get_research_mission_repository,
    get_settings,
)
from baobab_pulse.api.runtime import CapabilityApiRuntime
from baobab_pulse.application.services.evidence_search_capability import (
    EvidenceSearchCapabilityService,
)
from baobab_pulse.application.services.research_mission_manage_capability import (
    ResearchMissionManageCapabilityService,
)
from baobab_pulse.configuration.settings import Environment, Settings
from baobab_pulse.infrastructure.authentication.oidc_jwks import (
    OidcJwksWorkloadAuthenticator,
)
from baobab_pulse.infrastructure.authentication.current_issuer_status import (
    CurrentIssuerStatusWorkloadAuthenticator,
)
from baobab_pulse.application.ports.authentication import WorkloadAuthenticatorPort
from baobab_pulse.infrastructure.control_plane.capability_invocation import HttpCapabilityInvocationAuthority
from baobab_pulse.infrastructure.control_plane.context_authority import (
    ClientCredentialsTokenProvider,
    HttpControlPlaneContextAuthority,
)
from baobab_pulse.infrastructure.persistence.evidence_read_audit import PostgresEvidenceReadAudit


def build_capability_runtime(
    settings: Settings | None = None,
) -> CapabilityApiRuntime | None:
    """Build real authority adapters when configured; production fails closed."""

    actual = settings or get_settings()
    required: dict[str, str | None] = {
        "iam_issuer_url": actual.iam_issuer_url,
        "iam_jwks_url": actual.iam_jwks_url,
        "iam_token_url": actual.iam_token_url,
        "iam_client_secret": (
            actual.iam_client_secret.get_secret_value() if actual.iam_client_secret is not None else None
        ),
        "control_plane_context_validation_url": actual.control_plane_context_validation_url,
        "control_plane_capability_resolution_url": actual.control_plane_capability_resolution_url,
        "capability_provider_id": actual.capability_provider_id,
        "engine_instance_id": actual.engine_instance_id,
    }
    present = {name for name, value in required.items() if value}
    if not present:
        # A connected N03 development worker may never silently become an
        # unprotected local component simply because ALL authority settings
        # disappeared. A partially configured status observer is likewise an
        # explicit admission attempt, not permission to disable the PEP.
        if actual.iam_native_n03_required or any((
            actual.iam_introspection_url,
            actual.iam_introspection_client_id,
            actual.iam_introspection_client_secret,
        )):
            raise RuntimeError(
                "N03 current issuer-status admission unavailable: "
                "canonical IAM/CP authority configuration missing"
            )
        if actual.environment in {Environment.STAGING, Environment.PRODUCTION}:
            raise RuntimeError(
                "protected Pulse requires IAM/JWKS/token and Control Plane "
                "context-validation authority configuration"
            )
        return None

    missing = sorted(name for name, value in required.items() if not value)
    if missing:
        raise RuntimeError("incomplete Pulse capability-authority configuration: " + ", ".join(missing))

    if actual.environment == Environment.PRODUCTION:
        insecure = sorted(
            name
            for name in (
                "iam_issuer_url",
                "iam_jwks_url",
                "iam_token_url",
                "control_plane_context_validation_url",
                "control_plane_capability_resolution_url",
            )
            if urllib.parse.urlsplit(required[name] or "").scheme.lower() != "https"
        )
        if insecure:
            raise RuntimeError(
                "production Pulse capability authorities require HTTPS: " + ", ".join(insecure)
            )

    secret = actual.iam_client_secret
    assert secret is not None
    assert actual.iam_issuer_url is not None
    assert actual.iam_jwks_url is not None
    assert actual.iam_token_url is not None
    assert actual.control_plane_context_validation_url is not None

    authenticator: WorkloadAuthenticatorPort = OidcJwksWorkloadAuthenticator(
        issuer=actual.iam_issuer_url,
        jwks_url=actual.iam_jwks_url,
        audience=actual.iam_resource_audience,
        algorithms=(actual.iam_jwt_algorithm,),
        max_token_lifetime_seconds=actual.iam_max_token_lifetime_seconds,
        clock_skew_seconds=actual.iam_clock_skew_seconds,
        http_timeout_seconds=actual.authority_http_timeout_seconds,
    )
    # N03 native resource admission: the signed JWT must ALSO be current at
    # the issuer at request time. No bearer-status cache or CP-validator secret
    # reuse is allowed. Protected environments fail startup until the separate
    # issuer-status observer is actually registered and configured.
    status_parts = {
        "iam_introspection_url": actual.iam_introspection_url,
        "iam_introspection_client_id": actual.iam_introspection_client_id,
        "iam_introspection_client_secret": (
            actual.iam_introspection_client_secret.get_secret_value()
            if actual.iam_introspection_client_secret is not None else None
        ),
    }
    status_configured = any(status_parts.values())
    protected = actual.environment in {Environment.STAGING, Environment.PRODUCTION}
    if protected or actual.iam_native_n03_required or status_configured:
        missing_status = sorted(name for name, value in status_parts.items() if not value)
        if missing_status:
            raise RuntimeError(
                "N03 current issuer-status admission unavailable: " + ", ".join(missing_status)
            )
        if actual.iam_introspection_client_id == actual.iam_client_id:
            raise RuntimeError("N03 issuer observer cannot reuse CP validator workload identity")
        assert actual.iam_introspection_url is not None
        assert actual.iam_introspection_client_id is not None
        assert actual.iam_introspection_client_secret is not None
        authenticator = CurrentIssuerStatusWorkloadAuthenticator(
            signed=authenticator,
            issuer=actual.iam_issuer_url,
            audience=actual.iam_resource_audience,
            introspection_url=actual.iam_introspection_url,
            introspection_client_id=actual.iam_introspection_client_id,
            introspection_client_secret=actual.iam_introspection_client_secret.get_secret_value(),
            timeout_seconds=actual.authority_http_timeout_seconds,
            allow_development_loopback_http=actual.environment in {
                Environment.LOCAL, Environment.DEVELOPMENT,
            },
        )

    validator_tokens = ClientCredentialsTokenProvider(
        token_url=actual.iam_token_url,
        client_id=actual.iam_client_id,
        client_secret=secret.get_secret_value(),
        scope="context:validate",
        timeout_seconds=actual.authority_http_timeout_seconds,
    )
    context_authority = HttpControlPlaneContextAuthority(
        validation_url=actual.control_plane_context_validation_url,
        validator_tokens=validator_tokens,
        timeout_seconds=actual.authority_http_timeout_seconds,
    )

    evidence = EvidenceSearchCapabilityService(
        context_authority=context_authority,
        retrieval=get_evidence_retrieval_service(),
        invocation_authority=HttpCapabilityInvocationAuthority(
            resolution_url=actual.control_plane_capability_resolution_url or "",
            provider_id=actual.capability_provider_id or "",
            engine_instance_id=actual.engine_instance_id or "",
        ),
        read_audit=PostgresEvidenceReadAudit(get_database()),
    )
    research = ResearchMissionManageCapabilityService(
        context_authority=context_authority,
        repository=get_research_mission_repository(),
        mutation_store=get_research_mission_mutation_store(),
        invocation_authority=HttpCapabilityInvocationAuthority(
            resolution_url=actual.control_plane_capability_resolution_url or "",
            provider_id=actual.capability_provider_id or "",
            engine_instance_id=actual.engine_instance_id or "",
            capability_key="intelligence.research-mission.manage",
        ),
    )
    return CapabilityApiRuntime(
        authenticator=authenticator,
        evidence_search=evidence,
        research_missions=research,
    )


__all__ = ["build_capability_runtime"]

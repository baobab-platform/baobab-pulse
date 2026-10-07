"""P-CAP-07 production composition for canonical capability routes."""

from __future__ import annotations

import urllib.parse

from baobab_pulse.api.dependencies import (
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
from baobab_pulse.infrastructure.control_plane.context_authority import (
    ClientCredentialsTokenProvider,
    HttpControlPlaneContextAuthority,
)


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
            actual.iam_client_secret.get_secret_value()
            if actual.iam_client_secret is not None
            else None
        ),
        "control_plane_context_validation_url":
            actual.control_plane_context_validation_url,
    }
    present = {name for name, value in required.items() if value}
    if not present:
        if actual.environment == Environment.PRODUCTION:
            raise RuntimeError(
                "production Pulse requires IAM/JWKS/token and Control Plane "
                "context-validation authority configuration"
            )
        return None

    missing = sorted(name for name, value in required.items() if not value)
    if missing:
        raise RuntimeError(
            "incomplete Pulse capability-authority configuration: "
            + ", ".join(missing)
        )

    if actual.environment == Environment.PRODUCTION:
        insecure = sorted(
            name
            for name in (
                "iam_issuer_url",
                "iam_jwks_url",
                "iam_token_url",
                "control_plane_context_validation_url",
            )
            if urllib.parse.urlsplit(required[name] or "").scheme.lower() != "https"
        )
        if insecure:
            raise RuntimeError(
                "production Pulse capability authorities require HTTPS: "
                + ", ".join(insecure)
            )

    secret = actual.iam_client_secret
    assert secret is not None
    assert actual.iam_issuer_url is not None
    assert actual.iam_jwks_url is not None
    assert actual.iam_token_url is not None
    assert actual.control_plane_context_validation_url is not None

    authenticator = OidcJwksWorkloadAuthenticator(
        issuer=actual.iam_issuer_url,
        jwks_url=actual.iam_jwks_url,
        audience=actual.iam_resource_audience,
        algorithms=(actual.iam_jwt_algorithm,),
        max_token_lifetime_seconds=actual.iam_max_token_lifetime_seconds,
        clock_skew_seconds=actual.iam_clock_skew_seconds,
        http_timeout_seconds=actual.authority_http_timeout_seconds,
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
    )
    research = ResearchMissionManageCapabilityService(
        context_authority=context_authority,
        repository=get_research_mission_repository(),
        mutation_store=get_research_mission_mutation_store(),
    )
    return CapabilityApiRuntime(
        authenticator=authenticator,
        evidence_search=evidence,
        research_missions=research,
    )


__all__ = ["build_capability_runtime"]

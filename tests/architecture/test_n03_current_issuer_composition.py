"""N03 fail-closed protected composition; no native runtime acceptance."""
from __future__ import annotations

import pytest
from pydantic import SecretStr

from baobab_pulse.api.composition import build_capability_runtime
from baobab_pulse.configuration.settings import Environment, Settings


def configured(environment: Environment, **extra) -> Settings:
    settings = {
        "environment": environment,
        "iam_issuer_url": "https://iam.example.invalid",
        "iam_jwks_url": "https://iam.example.invalid/.well-known/jwks.json",
        "iam_token_url": "https://iam.example.invalid/oauth2/token",
        "iam_client_id": "cp-pulse-validator",
        "iam_client_secret": SecretStr("v" * 40),
        "control_plane_context_validation_url": "https://cp.example.invalid/platform-context/validate",
        "control_plane_capability_resolution_url": "https://cp.example.invalid/capabilities/resolve",
        "capability_provider_id": "baobab-pulse.core",
        "engine_instance_id": "ei_pulsedev",
    }
    settings.update(extra)
    return Settings(_env_file=None, **settings)


@pytest.mark.parametrize("environment", [Environment.STAGING, Environment.PRODUCTION])
def test_protected_native_pep_cannot_start_jwks_only(environment: Environment) -> None:
    with pytest.raises(RuntimeError, match="N03 current issuer-status admission unavailable"):
        build_capability_runtime(configured(environment))


def test_n03_introspection_cannot_borrow_cp_context_validator_identity() -> None:
    with pytest.raises(RuntimeError, match="cannot reuse CP validator"):
        build_capability_runtime(configured(
            Environment.PRODUCTION,
            iam_introspection_url="https://iam.example.invalid/oauth2/introspect",
            iam_introspection_client_id="cp-pulse-validator",
            iam_introspection_client_secret=SecretStr("s" * 48),
        ))


def test_incomplete_dev_issuer_status_configuration_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="iam_introspection_client_secret"):
        build_capability_runtime(configured(
            Environment.DEVELOPMENT,
            iam_introspection_url="https://iam.example.invalid/oauth2/introspect",
            iam_introspection_client_id="pulse-introspection-observer",
        ))


def test_connected_development_requires_real_native_issuer_status() -> None:
    with pytest.raises(RuntimeError, match="N03 current issuer-status admission unavailable"):
        build_capability_runtime(configured(
            Environment.DEVELOPMENT, iam_native_n03_required=True,
        ))


def test_candidate_dev_does_not_silently_upgrade_provider_status() -> None:
    # The opt-in switch is a runtime denial fence, not an IAM registration,
    # a CP Context grant or a provider support promotion.
    settings = configured(Environment.DEVELOPMENT, iam_native_n03_required=True)
    assert settings.iam_native_n03_required is True
    assert settings.iam_introspection_client_id is None

"""Twelve-factor, fail-fast Pulse configuration (item 118-119).

Invalid production configuration SHALL fail fast with actionable errors —
``pydantic-settings`` gives this for free: constructing :class:`Settings`
raises ``pydantic.ValidationError`` naming exactly which environment
variable is missing or malformed, rather than the process starting and
failing confusingly on first use.

Provider credentials (``*_API_KEY``) are optional at this layer — the core
test suite and the deterministic reference pipeline never require one
(req. 96); a real ``ModelExecutionPort`` adapter that needs one fails
clearly at the point it is actually selected, not at settings-load time for
every deployment regardless of which provider it uses.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PULSE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Environment = Environment.LOCAL
    service_name: str = "baobab-pulse"
    log_level: str = "INFO"

    database_url: str = Field(
        default="postgresql://pulse:pulse@localhost:5432/baobab_pulse",
        description="PostgreSQL 17 connection string (ADR-PULSE parent spec §44).",
    )

    object_storage_endpoint: str | None = None
    object_storage_bucket: str = "baobab-pulse-evidence"
    object_storage_access_key: SecretStr | None = None
    object_storage_secret_key: SecretStr | None = None

    otel_exporter_otlp_endpoint: str | None = None
    otel_traces_enabled: bool = False

    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None

    # -- Qdrant (semantic-retrieval projection store — item 22 of the
    # Qdrant refactor; PostgreSQL above remains canonical) -------------------
    qdrant_url: str | None = Field(
        default="http://localhost:6333",
        description="Qdrant REST endpoint. Set to None/empty with qdrant_location=':memory:' for "
        "an embedded, in-process Qdrant (used by the default test suite — no server required).",
    )
    qdrant_location: str | None = None
    """Set to ``":memory:"`` (qdrant_client's own sentinel) to use Qdrant's
    embedded in-process mode instead of ``qdrant_url`` (item 80: unit tests
    never require a live Qdrant server). Unset in every real deployment."""
    qdrant_api_key: SecretStr | None = None
    qdrant_tls: bool = False
    qdrant_timeout_seconds: float = 5.0
    qdrant_collection_prefix: str = "baobab-pulse"
    qdrant_evidence_collection_version: str = "v1"
    """Physical collection version for the ``evidence`` logical collection
    (item 26). Bump this — as part of a new deployment, after backfilling
    the new version via the rebuild workflow — to reindex without an
    in-place, potentially destructive migration."""

    embedding_provider: str = "mock"
    """Provider-neutral (item 19, 52): ``"mock"`` is the only supported
    value today (deterministic, no credentials/model download). Adding a
    real provider is a separate, later, controlled change — see
    ``infrastructure.haystack.embedders.embedding_adapter``."""
    embedding_model_id: str = "mock-model"
    embedding_dimension: int = 768

    # -- P-CAP-07 production capability authority -------------------------
    iam_issuer_url: str | None = None
    iam_jwks_url: str | None = None
    iam_token_url: str | None = None
    iam_client_id: str = "baobab-pulse-workload"
    iam_client_secret: SecretStr | None = None
    iam_resource_audience: str = "baobab-pulse"
    iam_jwt_algorithm: str = "RS256"
    iam_max_token_lifetime_seconds: int = 900
    iam_clock_skew_seconds: int = 30
    control_plane_context_validation_url: str | None = None
    authority_http_timeout_seconds: float = 5.0

    api_host: str = "0.0.0.0"  # noqa: S104 -- container-internal bind, fronted by an ingress/load balancer
    api_port: int = 8000

    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

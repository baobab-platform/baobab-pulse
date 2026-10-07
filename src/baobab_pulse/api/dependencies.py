"""FastAPI dependency wiring — the composition root for the API process.

Kept in one small module rather than scattered ``Depends()`` factories
throughout routers, so the wiring between ports and their infrastructure
implementations is visible in one place (item 128: "domain/application/
ports/infrastructure boundaries").
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Header, Request

from baobab_pulse.api.runtime import CapabilityApiRuntime
from baobab_pulse.application.ports.authentication import (
    AuthenticatedCaller,
    WorkloadAuthenticationError,
    WorkloadAuthenticationUnavailableError,
)
from baobab_pulse.application.ports.vector_projection_port import ProjectionCollection
from baobab_pulse.application.services.evidence_retrieval_service import EvidenceRetrievalService
from baobab_pulse.application.services.research_mission_service import ResearchMissionService
from baobab_pulse.configuration.settings import Settings
from baobab_pulse.contracts.mutations import validate_idempotency_key
from baobab_pulse.domain.shared.errors import (
    CapabilityAuthenticationError,
    CapabilityAuthorityUnavailableError,
    CapabilityInvalidRequestError,
    CapabilityRuntimeUnavailableError,
)
from baobab_pulse.infrastructure.haystack.document_stores.qdrant_projection_store import (
    QdrantEvidenceProjectionStore,
    resolve_collection_name,
)
from baobab_pulse.infrastructure.haystack.embedders.embedding_adapter import (
    HaystackEmbeddingAdapter,
    build_document_embedder,
    build_text_embedder,
)
from baobab_pulse.infrastructure.haystack.pipeline_adapter import HaystackPipelineAdapter
from baobab_pulse.infrastructure.persistence.connection import Database
from baobab_pulse.infrastructure.persistence.evidence_repository import PostgresEvidenceSetRepository
from baobab_pulse.infrastructure.persistence.research_mission_mutation import (
    PostgresResearchMissionMutationStore,
)
from baobab_pulse.infrastructure.persistence.research_mission_repository import (
    PostgresResearchMissionRepository,
)


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_database() -> Database:
    return Database(get_settings().database_url)


@lru_cache
def get_research_mission_repository() -> PostgresResearchMissionRepository:
    """Durable canonical ResearchMission persistence (P-CAP-04)."""
    return PostgresResearchMissionRepository(get_database())


@lru_cache
def get_research_mission_mutation_store() -> PostgresResearchMissionMutationStore:
    """Atomic idempotency/audit/outbox persistence for P-CAP-05 CREATE."""
    return PostgresResearchMissionMutationStore(get_database())


@lru_cache
def get_research_mission_service() -> ResearchMissionService:
    return ResearchMissionService(pipeline_port=HaystackPipelineAdapter())


@lru_cache
def get_evidence_repository() -> PostgresEvidenceSetRepository:
    return PostgresEvidenceSetRepository(get_database())


@lru_cache
def get_embedding_port() -> HaystackEmbeddingAdapter:
    settings = get_settings()
    return HaystackEmbeddingAdapter(
        text_embedder=build_text_embedder(
            settings.embedding_provider, dimension=settings.embedding_dimension, model=settings.embedding_model_id
        ),
        document_embedder=build_document_embedder(
            settings.embedding_provider, dimension=settings.embedding_dimension, model=settings.embedding_model_id
        ),
        model_id=f"{settings.embedding_provider}:{settings.embedding_model_id}",
        model_version="1",
    )


@lru_cache
def get_qdrant_evidence_store() -> QdrantEvidenceProjectionStore:
    settings = get_settings()
    return QdrantEvidenceProjectionStore(
        get_embedding_port(),
        collection_name=resolve_collection_name(
            ProjectionCollection.EVIDENCE,
            prefix=settings.qdrant_collection_prefix,
            version=settings.qdrant_evidence_collection_version,
        ),
        url=settings.qdrant_url,
        location=settings.qdrant_location,
        api_key=settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None,
        https=settings.qdrant_tls,
        timeout=settings.qdrant_timeout_seconds,
    )


@lru_cache
def get_evidence_retrieval_service() -> EvidenceRetrievalService:
    return EvidenceRetrievalService(
        semantic_retrieval=get_qdrant_evidence_store(), hydration=get_evidence_repository()
    )


@dataclass(frozen=True, slots=True)
class AuthenticatedCapabilityRequest:
    """Verified caller plus the canonical capability runtime."""

    caller: AuthenticatedCaller
    runtime: CapabilityApiRuntime


@dataclass(frozen=True, slots=True)
class CapabilityRequestMetadata:
    """Trusted request metadata used by mutation-governance logic."""

    correlation_id: UUID
    idempotency_key: str | None


def _capability_runtime(request: Request) -> CapabilityApiRuntime:
    runtime = getattr(request.app.state, "capability_runtime", None)
    if not isinstance(runtime, CapabilityApiRuntime):
        raise CapabilityRuntimeUnavailableError(
            "canonical Pulse capability runtime is not configured"
        )
    return runtime


def _bearer_token(authorization: str | None) -> str:
    if authorization is None:
        raise CapabilityAuthenticationError("a bearer token is required")
    scheme, separator, token = authorization.partition(" ")
    token = token.strip()
    if separator != " " or scheme.lower() != "bearer" or not 16 <= len(token) <= 8192:
        raise CapabilityAuthenticationError("Authorization must contain a valid Bearer token")
    return token


async def require_authenticated_capability_request(
    request: Request,
) -> AuthenticatedCapabilityRequest:
    """Authenticate the actual caller; never infer identity from request fields."""

    token = _bearer_token(request.headers.get("Authorization"))
    runtime = _capability_runtime(request)
    try:
        caller = await runtime.authenticator.authenticate(token)
    except WorkloadAuthenticationError as exc:
        raise CapabilityAuthenticationError(
            "the bearer token could not be verified"
        ) from exc
    except WorkloadAuthenticationUnavailableError as exc:
        raise CapabilityAuthorityUnavailableError(
            "the workload authentication authority is unavailable"
        ) from exc

    if caller.access_token != token:
        caller = replace(caller, access_token=token)
    return AuthenticatedCapabilityRequest(caller=caller, runtime=runtime)


async def require_context_id(
    x_baobab_context_id: Annotated[
        str | None,
        Header(alias="X-Baobab-Context-Id"),
    ] = None,
) -> UUID:
    """Require the opaque CP context handle without accepting tenant authority."""

    if x_baobab_context_id is None:
        raise CapabilityInvalidRequestError("X-Baobab-Context-Id is required")
    try:
        return UUID(x_baobab_context_id)
    except ValueError as exc:
        raise CapabilityInvalidRequestError(
            "X-Baobab-Context-Id must be a UUID"
        ) from exc


async def get_capability_request_metadata(
    request: Request,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key"),
    ] = None,
) -> CapabilityRequestMetadata:
    """Validate correlation and optional mutation idempotency metadata."""

    raw_correlation_id = getattr(request.state, "correlation_id", None)
    try:
        correlation_id = UUID(str(raw_correlation_id))
    except (TypeError, ValueError) as exc:
        replacement = uuid4()
        request.state.correlation_id = str(replacement)
        raise CapabilityInvalidRequestError(
            "X-Correlation-Id must be a UUID when supplied"
        ) from exc

    if idempotency_key is not None:
        try:
            idempotency_key = validate_idempotency_key(idempotency_key)
        except ValueError as exc:
            raise CapabilityInvalidRequestError(str(exc)) from exc

    return CapabilityRequestMetadata(
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
    )

"""Domain-level errors.

These are the only exceptions the domain layer raises. Infrastructure and
provider-specific exceptions (Haystack, asyncpg, httpx, ...) are translated
into these — or into ``baobab_pulse.infrastructure`` error types that
subclass :class:`PulseError` — at the relevant anti-corruption boundary; they
never cross into application/domain code directly (req. #120).
"""

from __future__ import annotations


class PulseError(Exception):
    """Base for every error raised by Pulse's own domain/application code."""


class InvariantViolation(PulseError):
    """Raised when an aggregate invariant defined in ADR-PULSE-002 (or a
    domain-specific ADR) would otherwise be violated."""


class ImmutableObjectError(PulseError):
    """Raised when code attempts to mutate a value that ADR-PULSE-002/004
    require to be immutable or append-only (e.g. a published Observation,
    a frozen EvidenceSet, a committed SourceArtefact)."""


class TenantContextMissingError(PulseError):
    """Raised when tenant-scoped application execution is attempted without
    an established :class:`~baobab_pulse.tenancy.context.TenantContext`
    (architecture invariant: tenant context cannot be silently omitted)."""


class VectorStoreUnavailable(PulseError):
    """Raised when the Qdrant vector store cannot be reached at all
    (connection refused, timeout, TLS failure). Qdrant is eventually
    consistent, derived infrastructure (Qdrant refactor item 35-36): this
    error SHALL never be raised from, or cause a rollback of, a canonical
    PostgreSQL transaction — only from a semantic-retrieval or
    projection-write code path."""


class SemanticRetrievalUnavailable(VectorStoreUnavailable):
    """Raised by :class:`~baobab_pulse.application.ports.semantic_retrieval_port.SemanticRetrievalPort`
    when a search cannot be served. Callers SHOULD treat this as a
    degraded/retryable failure of semantic search specifically — never as
    "Pulse is down" (item 36)."""


class ProjectionWriteFailed(PulseError):
    """Raised by :class:`~baobab_pulse.application.ports.vector_projection_port.VectorProjectionPort`
    when a single upsert/delete fails. Does not imply canonical PostgreSQL
    state is wrong — only that its projection into Qdrant did not land and
    should be retried or rebuilt."""


class ProjectionRebuildFailed(PulseError):
    """Raised when a full projection rebuild (item 32, 75) fails partway
    through. The rebuild workflow is designed to be safely re-run: a
    partial rebuild leaves canonical PostgreSQL data untouched and callers
    can re-invoke the rebuild once the underlying cause is fixed."""


class CapabilityInvalidRequestError(PulseError):
    """Canonical capability invocation metadata is malformed or missing."""


class CapabilityAuthenticationError(PulseError):
    """The inbound caller could not be authenticated."""


class CapabilityAccessDeniedError(PulseError):
    """The authenticated caller is not authorised for the requested context."""


class CapabilityContextNotFoundError(PulseError):
    """The caller-bound Control Plane context is unavailable."""


class CapabilityAuthorityUnavailableError(PulseError):
    """A required IAM or Control Plane authority is unavailable."""


class CapabilityRuntimeUnavailableError(PulseError):
    """The canonical capability runtime has not been configured."""


class ResearchMissionNotFoundError(PulseError):
    """A ResearchMission is absent from the caller-bound tenant scope."""

class IdempotencyConflictError(PulseError):
    """An idempotency key is already bound to a different mutation request."""


class MutationPersistenceUnavailableError(PulseError):
    """The durable mutation-governance store is unavailable."""


class MutationIntegrityError(PulseError):
    """Persisted mutation, audit or outbox state violates integrity invariants."""

"""EmbeddingPort — the embedding boundary (Qdrant refactor item 19).

Canonical/application code never depends directly on one embedding
provider. Today's default implementation
(``infrastructure.haystack.embedders.embedding_adapter``) wraps Haystack's
deterministic ``MockTextEmbedder``/``MockDocumentEmbedder`` so the core test
suite and the projection rebuild path never require a model-provider API
key or a downloaded model — the same principle already applied to
``ModelExecutionPort``/``MockChatGenerator``.

Migrating to a real embedding model (e.g. a sentence-transformer or an
OpenAI embedding endpoint) is a future, separately-reviewed change: this
refactor's job is to make Qdrant work with whatever embedding profile is
configured, not to pick a production embedding model (item 52).
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict


class EmbeddingVector(BaseModel):
    """A plain, framework-agnostic embedding result.

    Never a ``numpy`` array or provider-specific tensor type — just the
    float components plus enough identity to detect a model change later
    (item 53: embedding provider, model, version, dimension)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    values: tuple[float, ...]
    model_id: str
    model_version: str

    @property
    def dimension(self) -> int:
        return len(self.values)


class EmbeddingPort(Protocol):
    """Implemented today by
    ``infrastructure.haystack.embedders.embedding_adapter.HaystackEmbeddingAdapter``.
    """

    async def embed_text(self, text: str) -> EmbeddingVector:
        """Embed a single query string (asymmetric-search text side)."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingVector]:
        """Embed a batch of documents/content (asymmetric-search document
        side) — a separate method from :meth:`embed_text` because some
        embedding models use different encoders for queries vs. documents."""
        ...

    def model_identity(self) -> str:
        """A stable identifier for the configured embedding model, e.g.
        ``"mock"`` or ``"openai:text-embedding-3-small"`` — never a bare
        version number alone (item 53)."""
        ...

    def dimension(self) -> int:
        """The vector dimension this embedder produces. The Qdrant adapter
        configures its collection from this value — it is never
        hard-coded in business code (item 54)."""
        ...

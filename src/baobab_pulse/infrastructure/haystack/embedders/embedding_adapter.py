"""HaystackEmbeddingAdapter — implements ``EmbeddingPort``.

Defaults to Haystack's deterministic ``MockTextEmbedder``/
``MockDocumentEmbedder`` (item 96-97 of the platform brief: the core test
suite and the projection rebuild path never require a model-provider API
key or a downloaded model) — the same pattern already used for
``ModelExecutionPort``/``MockChatGenerator``.

Making the *current* embedding model (there isn't one yet — this is the
first embedding capability this codebase has, per the Qdrant-refactor
discovery report) work through Qdrant is this refactor's job; swapping in a
real provider (sentence-transformers, OpenAI, ...) is a separate, later,
controlled change (item 52) — ``build_text_embedder``/``build_document_embedder``
is where that swap happens, and nowhere else.
"""

from __future__ import annotations

from typing import Any

from haystack.components.embedders import MockDocumentEmbedder, MockTextEmbedder
from haystack.dataclasses import Document

from baobab_pulse.application.ports.embedding_port import EmbeddingVector
from baobab_pulse.infrastructure.haystack.errors import translate_exceptions


def build_text_embedder(provider: str, *, dimension: int = 768, model: str | None = None) -> Any:
    """Provider-neutral factory (item 19, 37). ``provider`` is a Pulse-owned
    label — never a Haystack class name leaking into calling code."""
    if provider == "mock":
        return MockTextEmbedder(dimension=dimension, model=model or "mock-model")
    raise ValueError(
        f"unknown embedding provider {provider!r} — register a new branch here when Pulse adds provider "
        "support; do not hard-wire a provider name anywhere outside this factory"
    )


def build_document_embedder(provider: str, *, dimension: int = 768, model: str | None = None) -> Any:
    if provider == "mock":
        return MockDocumentEmbedder(dimension=dimension, model=model or "mock-model")
    raise ValueError(
        f"unknown embedding provider {provider!r} — register a new branch here when Pulse adds provider "
        "support; do not hard-wire a provider name anywhere outside this factory"
    )


class HaystackEmbeddingAdapter:
    """Implements ``application.ports.embedding_port.EmbeddingPort``."""

    def __init__(self, text_embedder: Any, document_embedder: Any, *, model_id: str, model_version: str) -> None:
        self._text_embedder = text_embedder
        self._document_embedder = document_embedder
        self._model_id = model_id
        self._model_version = model_version

    async def embed_text(self, text: str) -> EmbeddingVector:
        return self._embed_text(text)

    @translate_exceptions("Haystack text embedding")
    def _embed_text(self, text: str) -> EmbeddingVector:
        result = self._text_embedder.run(text)
        return EmbeddingVector(
            values=tuple(result["embedding"]), model_id=self._model_id, model_version=self._model_version
        )

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingVector]:
        return self._embed_batch(texts)

    @translate_exceptions("Haystack document embedding")
    def _embed_batch(self, texts: list[str]) -> list[EmbeddingVector]:
        documents = [Document(content=text) for text in texts]
        result = self._document_embedder.run(documents)
        return [
            EmbeddingVector(
                values=tuple(document.embedding or ()),
                model_id=self._model_id,
                model_version=self._model_version,
            )
            for document in result["documents"]
        ]

    def model_identity(self) -> str:
        return self._model_id

    def dimension(self) -> int:
        return int(self._text_embedder.dimension)

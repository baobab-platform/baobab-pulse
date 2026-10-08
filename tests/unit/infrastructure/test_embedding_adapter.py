"""HaystackEmbeddingAdapter / build_text_embedder / build_document_embedder
(Qdrant refactor item 19, 52-54): the ``mock`` provider is deterministic and
credential-free, and an unregistered provider name fails loudly rather than
silently falling back to something unexpected.
"""

from __future__ import annotations

import pytest

from baobab_pulse.infrastructure.haystack.embedders.embedding_adapter import (
    HaystackEmbeddingAdapter,
    build_document_embedder,
    build_text_embedder,
)


def test_build_text_embedder_unknown_provider_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unknown embedding provider"):
        build_text_embedder("not-a-real-provider")


def test_build_document_embedder_unknown_provider_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unknown embedding provider"):
        build_document_embedder("not-a-real-provider")


def _adapter(dimension: int = 8) -> HaystackEmbeddingAdapter:
    return HaystackEmbeddingAdapter(
        text_embedder=build_text_embedder("mock", dimension=dimension),
        document_embedder=build_document_embedder("mock", dimension=dimension),
        model_id="mock:test-model",
        model_version="3",
    )


async def test_embed_text_returns_a_vector_of_the_configured_dimension() -> None:
    adapter = _adapter(dimension=8)

    vector = await adapter.embed_text("Ugandan coffee exports rose 18% year-on-year.")

    assert len(vector.values) == 8
    assert vector.dimension == 8
    assert vector.model_id == "mock:test-model"
    assert vector.model_version == "3"


async def test_embed_text_is_deterministic_for_the_same_input() -> None:
    adapter = _adapter()

    first = await adapter.embed_text("same text")
    second = await adapter.embed_text("same text")

    assert first.values == second.values


async def test_embed_text_differs_for_different_input() -> None:
    adapter = _adapter()

    first = await adapter.embed_text("alpha")
    second = await adapter.embed_text("beta")

    assert first.values != second.values


async def test_embed_batch_returns_one_vector_per_input_text() -> None:
    adapter = _adapter(dimension=4)

    vectors = await adapter.embed_batch(["first document", "second document", "third document"])

    assert len(vectors) == 3
    assert all(len(vector.values) == 4 for vector in vectors)
    assert all(vector.model_id == "mock:test-model" and vector.model_version == "3" for vector in vectors)


def test_dimension_reports_the_configured_dimension() -> None:
    adapter = _adapter(dimension=32)
    assert adapter.dimension() == 32


def test_model_identity_reports_the_configured_model_id() -> None:
    adapter = _adapter()
    assert adapter.model_identity() == "mock:test-model"

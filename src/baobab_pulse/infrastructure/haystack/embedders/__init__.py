"""Binds the ``EmbeddingPort`` to a concrete Haystack embedder.

Provider-neutral by construction (item 19, 37 of the Haystack ADR/platform
brief pattern): ``build_text_embedder``/``build_document_embedder`` are the
only place a provider string turns into an actual Haystack embedder class,
mirroring ``infrastructure.haystack.generators.model_execution_adapter``.
"""

"""Classification enforcement (item 51, 70).

A retriever SHALL NOT retrieve evidence outside the authorised
tenant/context/classification boundary and expect the LLM to ignore it
(item 50) — filtering happens here, structurally, before anything reaches a
Haystack retriever or generator. See
``infrastructure.haystack.document_stores.in_memory_projection`` for where
this is actually applied to a retrieval projection.
"""

from __future__ import annotations

from baobab_pulse.domain.shared.enums import Classification

_CLEARANCE_ORDER = (
    Classification.PUBLIC,
    Classification.BAOBAB_INTERNAL,
    Classification.TENANT,
    Classification.CONFIDENTIAL,
    Classification.RESTRICTED,
)


def may_access(*, requester_clearance: Classification, object_classification: Classification) -> bool:
    """Return whether a requester cleared for ``requester_clearance`` may
    access an object classified at ``object_classification``.

    This is a structural, code-level gate — it has no concept of "the model
    was told not to look" (item 41, 81: external evidence and prompt
    instructions are never a substitute for enforcement).
    """
    return _CLEARANCE_ORDER.index(requester_clearance) >= _CLEARANCE_ORDER.index(object_classification)


def allowed_classifications(requester_clearance: Classification) -> tuple[Classification, ...]:
    """Every classification level ``requester_clearance`` may access.

    Used to build a Qdrant/Haystack ``in`` filter *before* a semantic query
    is issued (item 45-46: classification filtering happens structurally,
    not by post-filtering an unrestricted result set).
    """
    ceiling = _CLEARANCE_ORDER.index(requester_clearance)
    return _CLEARANCE_ORDER[: ceiling + 1]

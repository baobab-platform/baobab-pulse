"""Cross-boundary contracts: the wire shapes Pulse's API and event outbox
actually emit.

These mirror ``baobab-platform/shared``'s canonical schemas field-for-field
(``contracts/events/v1/envelope.schema.json`` and
``contracts/errors/v1/problem-details.schema.json``) rather than inventing a
Pulse-local shape — item 56: "If an organisational contract already exists,
reuse it." ``tests/contract/`` validates instances of these models against
vendored copies of those JSON Schemas so a drift between this module and the
org contract fails CI, not a cross-engine integration months later.
"""

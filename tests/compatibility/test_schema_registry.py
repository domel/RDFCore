"""Pinned RDFLib names and additive Schema WD 2026-10-22 registry entries."""

import rdfcore


def test_registry_presence_does_not_add_external_reasoning_rules():
    from rdfcore.semantics import entails

    assert (
        entails(
            [],
            [(rdfcore.RDF.CompoundLiteral, rdfcore.RDF.type, rdfcore.RDFS.Class)],
            regime="rdfs",
            mode="decide",
        )
        is False
    )

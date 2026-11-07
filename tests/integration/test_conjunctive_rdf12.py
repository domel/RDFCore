"""RDF 1.2 extensions preserve ConjunctiveGraph context boundaries.

Concepts CR 2026-04-07 §4; TriG/N-Quads WD 2026-10-23 §2.
Editors' Drafts checked 2026-11-04: same default/named graph distinction.
"""

from rdfcore import ConjunctiveGraph, Dataset, URIRef
from rdfcore.compare import isomorphic
from rdfcore.semantics import merge_datasets


S, P, O = map(URIRef, ("urn:s", "urn:p", "urn:o"))


def test_comparison_is_read_only_and_dataset_ids_stay_distinct():
    source = ConjunctiveGraph(identifier=URIRef("urn:default"))
    source.default_context.base = "urn:base"
    source.add((S, P, O))
    source.graph(URIRef("urn:empty"), base="urn:named-base")
    target = Dataset().add((S, P, O))
    target.graph(URIRef("urn:empty"))
    before = list(source.store.contexts()), dict(source._graphs)
    assert isomorphic(source, target)
    assert (list(source.store.contexts()), source._graphs) == before
    assert source.default_context.base == "urn:base"
    assert source._graphs[URIRef("urn:empty")].base == "urn:named-base"
    merged = merge_datasets([source])
    assert set(merged.default_graph) == {(S, P, O)}

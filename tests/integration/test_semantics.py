"""Optional semantics: published Semantics 2026-09-24, Schema 2026-10-10.

These are section-derived regressions, not a full W3C conformance run.
"""

import pytest

from rdfcore import BNode, Dataset, Graph, Literal, RDF, RDFS, TripleTerm, URIRef, Variable
from rdfcore.semantics import UnsupportedEntailment, entailment_closure, entails


S, P, O, Q, C, D, E = map(URIRef, ("urn:s", "urn:p", "urn:o", "urn:q", "urn:C", "urn:D", "urn:E"))


def test_simple_empty_duplicates_and_direction():
    assert entails([], []) is True
    assert entails([(S, P, O)] * 2, [(S, P, O)]) is True
    assert entails([], [(S, P, O)]) is False
    assert entails([(BNode("a"), P, O)], [(S, P, O)]) is False


def test_homomorphism_is_consistent_and_not_injective():
    x, y = BNode("x"), BNode("y")
    assert entails([(S, P, O)], [(x, P, O), (y, P, O)])
    assert not entails([(S, P, O), (O, Q, S)], [(x, P, O), (x, Q, S)])
    # Matching must backtrack rather than commit to the first candidate.
    assert entails([(S, P, O), (O, P, O), (O, Q, S)], [(x, P, O), (x, Q, S)])


def test_nested_transparency_and_global_blank_node_scope():
    x = BNode("x")
    term = TripleTerm(S, P, TripleTerm(O, Q, Literal("v")))
    source = [(S, Q, term), (S, P, O)]
    target = [(x, Q, TripleTerm(x, P, TripleTerm(O, Q, Literal("v"))))]
    assert entails(source, target)
    assert not entails(source, target + [(x, P, S)])
    assert not entails(source, [(O, Q, Literal("v"))])
    assert entails(source, [(S, Q, BNode("whole"))])


def test_literals_preserve_lexical_identity_and_direction():
    integer = URIRef("http://www.w3.org/2001/XMLSchema#integer")
    assert not entails([(S, P, Literal("01", datatype=integer, normalize=False))],
                       [(S, P, Literal("1", datatype=integer, normalize=False))])
    assert entails([(S, P, Literal("v"))],
                   [(S, P, Literal("v", datatype=URIRef("http://www.w3.org/2001/XMLSchema#string")))])
    assert entails([(S, P, TripleTerm(S, P, Literal("v", lang="en", direction="ltr")))],
                   [(S, P, TripleTerm(S, P, Literal("v", lang="EN", direction="ltr")))])
    assert not entails([(S, P, Literal("v", lang="en", direction="ltr"))],
                       [(S, P, Literal("v", lang="en", direction="rtl"))])


@pytest.mark.parametrize("regime", ["rdf", "rdfs"])
def test_rdf_property_proof_and_unknown_is_not_false(regime):
    assert entails([(S, P, O)], [(P, RDF.type, RDF.Property)], regime=regime)
    with pytest.raises(UnsupportedEntailment):
        entails([], [(S, P, O)], regime=regime)


def test_rdfs_fixed_point_domain_range_and_hierarchy():
    source = [(P, RDFS.subPropertyOf, Q), (Q, RDFS.domain, C),
              (Q, RDFS.range, D), (C, RDFS.subClassOf, D),
              (D, RDFS.subClassOf, E), (S, P, O)]
    expected = [(S, Q, O), (S, RDF.type, E), (O, RDF.type, E),
                (C, RDFS.subClassOf, E)]
    assert entails(source, expected, regime="rdfs")
    assert not entails(source, expected)
    with pytest.raises(UnsupportedEntailment):
        entails(source, [(E, RDFS.subClassOf, C)], regime="rdfs")
    closure = entailment_closure(source, regime="rdfs")
    assert set(expected) <= closure
    assert closure == entailment_closure(source, regime="rdfs")


def test_generalized_intermediates_support_blank_property_and_proposition():
    prop, value = BNode("prop"), BNode("value")
    assert entails([(P, RDFS.subPropertyOf, prop), (prop, RDFS.domain, C), (S, P, O)],
                   [(S, RDF.type, C)], regime="rdfs")
    term = TripleTerm(S, P, O)
    source = [(S, Q, term)]
    assert entails(source, [(S, Q, value), (value, RDF.type, RDFS.Proposition)], regime="rdfs")
    assert (term, RDF.type, RDFS.Proposition) in entailment_closure(source, regime="rdfs")
    assert (S, P, O) not in entailment_closure(source, regime="rdfs")


def test_source_graph_is_unchanged_and_context_is_explicit():
    dataset = Dataset()
    graph = dataset.graph(URIRef("urn:graph"))
    graph.add((S, P, O))
    before = set(graph)
    assert entails(graph, [(P, RDF.type, RDF.Property)], regime="rdf")
    assert set(graph) == before
    assert not entails(dataset.default_graph, [(S, P, O)])
    with pytest.raises(UnsupportedEntailment, match="graph"):
        entails(dataset, [])


@pytest.mark.parametrize("bad", [None, [(S, P)], [(S, P, O, C)], [(Literal("s"), P, O)],
                                     [(S, BNode("p"), O)], [(S, P, Variable("x"))],
                                     [(S, P, "object")], [(TripleTerm(S, P, O), P, O)]])
def test_invalid_graphs(bad):
    with pytest.raises(TypeError):
        entails(bad, [])
    with pytest.raises(TypeError):
        entails([], bad)


def test_invalid_regime_and_unsupported_datatypes_axioms_inconsistency():
    with pytest.raises(ValueError, match="regime"):
        entails([], [], regime="owl")
    with pytest.raises(UnsupportedEntailment, match="datatype"):
        entails([], [], regime="rdf", datatypes={URIRef("urn:datatype")})
    assert entails([], [(RDF.nil, RDF.type, RDF.List)], regime="rdf")
    bad = Literal("bad", datatype=URIRef("http://www.w3.org/2001/XMLSchema#integer"), normalize=False)
    with pytest.raises(UnsupportedEntailment):
        entails([(S, P, TripleTerm(S, P, bad))], [(O, Q, C)], regime="rdf")
    assert entails([(S, P, bad)], [(S, P, bad)])


def test_schema_axioms_and_container_vocabulary():
    assert entails([], [(RDF.reifies, RDFS.range, RDFS.Proposition)], regime='rdfs')
    assert entails([(S, RDF.reifies, O)], [(O, RDF.type, RDFS.Proposition)], regime='rdfs')
    assert entails([], [(RDF['_273'], RDF.type, RDF.Property)], regime='rdf')
    assert entails([], [(RDF['_273'], RDFS.subPropertyOf, RDFS.member)], regime='rdfs')
    with pytest.raises(UnsupportedEntailment):
        entails([], [(RDF['_0'], RDF.type, RDF.Property)], regime='rdf')
    with pytest.raises(UnsupportedEntailment):
        entails([], [(RDF['_01'], RDFS.subPropertyOf, RDFS.member)], regime='rdfs')
    assert not entails([], [(RDF.nil, RDF.type, RDF.List)])

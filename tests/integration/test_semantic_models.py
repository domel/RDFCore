"""Semantics CRD 2026-09-24 §§7–9, beyond the official manifest."""

import pytest

from rdfcore import BNode, Literal, RDF, RDFS, TripleTerm, URIRef, XSD
from rdfcore.semantics import entails

S, P, O, C = map(URIRef, ("urn:s", "urn:p", "urn:o", "urn:C"))


def decide(source, target, **kw):
    return entails(source, target, mode="decide", regime=kw.pop("regime", "rdfs"), **kw)


def test_aliases_do_not_capture_target_blank_nodes_with_the_same_label():
    x = BNode("value")
    source = [(x, RDF.type, XSD.boolean), (RDF.type, RDF.type, XSD.boolean), (S, P, x)]
    assert decide(source, [(x, P, O)], datatypes={XSD.boolean}) is False


@pytest.mark.parametrize("node", [O, RDF.type])
def test_value_assignments_inside_nested_terms_do_not_change_public_grammar(node):
    x = BNode("value")
    source = [
        (node, RDF.type, XSD.boolean),
        (S, P, TripleTerm(node, P, TripleTerm(S, node, O))),
    ]
    target = [
        (S, P, TripleTerm(x, P, TripleTerm(S, node, O))),
        (x, RDF.type, XSD.boolean),
    ]
    assert decide(source, target, datatypes={XSD.boolean}) is True
    assert decide(source, [(node, P, O)], datatypes={XSD.boolean}) is False
    with pytest.raises(TypeError):
        TripleTerm(Literal(True), P, O)


def test_injective_constructor_values_cannot_merge_different_string_arguments():
    types = {XSD.nonNegativeInteger, XSD.nonPositiveInteger}
    source = [(P, RDFS.range, d) for d in types]
    source += [(S, P, TripleTerm(S, C, Literal(text))) for text in ("a", "b")]
    assert decide(source, False, datatypes=types) is True


def test_aliased_infinite_superproperty_is_not_a_finite_countermodel():
    from rdfcore.semantics import UnsupportedEntailment

    types = {XSD.nonNegativeInteger, XSD.nonPositiveInteger}
    q = URIRef("urn:superproperty")
    source = [
        (name, RDF.type, datatype)
        for name in (P, RDFS.subClassOf)
        for datatype in types
    ]
    source += [(RDFS.Resource, P, RDFS.Class), (RDFS.subClassOf, RDFS.subPropertyOf, q)]
    # Constructor totality plus reflexive subclass edges makes this true.
    # Until superproperty witnesses are supported, it must stay unknown,
    # rather than claiming the finite sample is a negative certificate.
    with pytest.raises(UnsupportedEntailment):
        decide(
            source,
            [(BNode("class"), q, TripleTerm(S, RDF.type, O))],
            datatypes=types,
            max_steps=1000000,
        )

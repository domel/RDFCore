"""Semantics CRD 2026-09-24 §§5/8/9; Schema WD 2026-10-22.

These tests do not turn a finite rule closure into a general decision procedure.
"""

from rdfcore import BNode, RDF, RDFS, TripleTerm, URIRef
from rdfcore.semantics import entails

S, P, O, Q, C, D = map(URIRef, ("urn:s", "urn:p", "urn:o", "urn:q", "urn:C", "urn:D"))


def decide(source, target, regime="rdfs", **kwargs):
    return entails(source, target, regime=regime, mode="decide", **kwargs)


def test_constructor_existence_is_not_limited_to_terms_already_in_the_premise():
    source = [(RDFS.Resource, RDFS.subClassOf, RDFS.Class)]
    term = TripleTerm(S, RDF.type, O)
    x = BNode("class")
    assert decide(source, [(x, RDFS.subClassOf, term)]) is True
    prop = BNode("property")
    nested = TripleTerm(prop, RDF.type, TripleTerm(prop, RDF.type, O))
    assert (
        decide(source, [(prop, RDF.type, RDF.Property), (x, RDFS.subClassOf, nested)])
        is True
    )

import pytest

from rdfcore import BNode, ClosedNamespace, Graph, Literal, Memory, URIRef, XSD
from rdfcore.namespace import NamespaceManager


def test_graph_contexts_are_isolated_when_sharing_a_store():
    store = Memory()
    default = Graph(store=store)
    named = Graph(store=store, identifier=URIRef("http://example.org/named"))
    triple = (URIRef("http://example.org/s"), URIRef("http://example.org/p"), URIRef("http://example.org/o"))
    named.add(triple)
    assert list(default) == []
    assert list(named) == [triple]


def test_graph_value_honours_all_bound_positions():
    graph = Graph()
    triple = (URIRef("http://example.org/s"), URIRef("http://example.org/p"), URIRef("http://example.org/o"))
    graph.add(triple)
    assert graph.value(URIRef("http://example.org/other"), triple[1], triple[2]) is None


def test_invalid_literal_is_not_an_exception_and_keeps_its_lexical_form():
    literal = Literal("not-an-integer", datatype=XSD.integer)
    assert literal.ill_typed
    assert str(literal) == "not-an-integer"


def test_literal_copy_preserves_language():
    assert Literal(Literal("colour", lang="EN")).language == "EN"


def test_graph_rejects_invalid_rdf_terms():
    with pytest.raises(TypeError):
        Graph().add(("not-a-node", URIRef("http://example.org/p"), Literal("x")))


def test_closed_namespace_and_invalid_qname_local_name():
    ns = ClosedNamespace("http://example.org/", ["allowed"])
    assert str(ns.allowed) == "http://example.org/allowed"
    with pytest.raises(AttributeError):
        ns.other
    manager = NamespaceManager()
    manager.bind("ex", "http://example.org/")
    with pytest.raises(ValueError):
        manager.qname("http://example.org/_ contains-space")
    with pytest.raises(ValueError):
        NamespaceManager().compute_qname("http://example.org/0invalid")

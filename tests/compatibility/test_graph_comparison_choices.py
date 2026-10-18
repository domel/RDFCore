from rdfcore import BNode, Graph, Literal, URIRef
import pytest
import rdflib
import rdfcore


def test_graph_isomorphic_is_method_backed_by_compare():
    predicate = URIRef("urn:p")
    left = Graph().add((BNode("left"), predicate, Literal("x")))
    right = Graph().add((BNode("right"), predicate, Literal("x")))
    assert left.isomorphic(right)


def test_triples_choices_rejects_lists_in_multiple_positions_like_rdflib():
    for module in (rdflib, rdfcore):
        graph = module.Graph()
        subjects = [module.URIRef('urn:s')]
        predicates = [module.URIRef('urn:p')]
        graph.add((subjects[0], predicates[0], module.Literal('x')))
        with pytest.raises(AssertionError, match='subject / predicate'):
            list(graph.triples_choices((subjects, predicates, module.Literal('x'))))

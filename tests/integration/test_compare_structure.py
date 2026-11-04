"""Exact structural identity, distinct from RDFLib's approximate graph method."""
import random

import pytest
import rdflib
from rdflib.compare import isomorphic as reference_isomorphic

from rdfcore import BNode, Dataset, Graph, Literal, TripleTerm, URIRef
from rdfcore.compare import isomorphic


def cycles(module, sizes, prefix):
    graph = module.Graph()
    for part, size in enumerate(sizes):
        for index in range(size):
            graph.add((module.BNode(f'{prefix}{part}-{index}'), module.URIRef('urn:p'),
                       module.BNode(f'{prefix}{part}-{(index + 1) % size}')))
    return graph


@pytest.mark.parametrize('left,right,expected', [
    ([6], [6], True), ([6], [3, 3], False),
    ([3, 4, 3], [3, 3, 4], True), ([3, 3, 4], [5, 5], False),
])
def test_exact_cycles_and_repeated_components_match_reference(left, right, expected):
    assert reference_isomorphic(cycles(rdflib, left, 'a'), cycles(rdflib, right, 'b')) is expected
    assert isomorphic(cycles(__import__('rdfcore'), left, 'a'),
                      cycles(__import__('rdfcore'), right, 'b')) is expected


@pytest.mark.parametrize('seed', range(24))
def test_small_structures_agree_with_independent_oracle(seed):
    rng = random.Random(seed)
    edges = {(rng.randrange(5), rng.randrange(5)) for _ in range(8)}
    permutation = list(range(5))
    rng.shuffle(permutation)
    other = {(permutation[a], permutation[b]) for a, b in edges}
    if seed % 2:
        other.add((rng.randrange(5), rng.randrange(5)))

    def build(module, rows, prefix):
        graph = module.Graph()
        for a, b in rows:
            graph.add((module.BNode(prefix + str(a)), module.URIRef('urn:p'), module.BNode(prefix + str(b))))
        return graph

    expected = reference_isomorphic(build(rdflib, edges, 'a'), build(rdflib, other, 'b'))
    import rdfcore
    assert isomorphic(build(rdfcore, edges, 'a'), build(rdfcore, other, 'b')) is expected


def test_large_identical_components_do_not_depend_on_python_recursion_depth():
    left, right = Graph(), Graph()
    for index in range(1600):
        left.add((BNode(f'a{index}'), URIRef('urn:p'), Literal('same')))
        right.add((BNode(f'b{index}'), URIRef('urn:p'), Literal('same')))
    assert isomorphic(left, right)
    right.set((BNode('b0'), URIRef('urn:p'), Literal('different')))
    assert not isomorphic(left, right)


def test_large_connected_component_uses_iterative_statement_matching():
    left, right = Graph(), Graph()
    for index in range(1300):
        predicate = URIRef(f'urn:edge{index}')
        left.add((BNode(f'a{index}'), predicate, BNode(f'a{index + 1}')))
        right.add((BNode(f'b{index}'), predicate, BNode(f'b{index + 1}')))
    assert isomorphic(left, right)


@pytest.mark.parametrize('mismatch', [False, True])
def test_nested_terms_share_one_mapping_with_graph_names(mismatch):
    left, right = Dataset(), Dataset()
    p = URIRef('urn:p')
    a, b = BNode('a'), BNode('b')
    left.graph(a)
    right.graph(b if not mismatch else BNode('separate'))
    ta, tb = a, b
    for _ in range(20):
        ta = TripleTerm(a, p, ta)
        tb = TripleTerm(b, p, tb)
    left.add((URIRef('urn:s'), p, ta))
    right.add((URIRef('urn:s'), p, tb))
    assert isomorphic(left, right) is (not mismatch)


def test_rdf11_method_keeps_reference_approximation_for_symmetric_graphs():
    import rdfcore
    outcomes = []
    for module in (rdflib, rdfcore):
        outcomes.append(cycles(module, [6], 'a').isomorphic(cycles(module, [3, 3], 'b')))
    assert outcomes == [True, True]
    assert not isomorphic(cycles(rdfcore, [6], 'a'), cycles(rdfcore, [3, 3], 'b'))

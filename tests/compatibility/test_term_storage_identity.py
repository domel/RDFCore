"""Term identity and graph observations against RDFLib 7.6.0."""

import pytest
import rdflib
import rdfcore


def pair(module, case):
    if case == 'integer':
        return module.Literal(1), module.Literal('1', datatype=module.XSD.integer)
    if case == 'boolean':
        return module.Literal(True), module.Literal('true', datatype=module.XSD.boolean)
    if case == 'language':
        return module.Literal('text', lang='EN'), module.Literal('text', lang='en')
    return (module.Literal('01', datatype=module.XSD.integer, normalize=False),
            module.Literal('1', datatype=module.XSD.integer, normalize=False))


@pytest.mark.parametrize('case', ['integer', 'boolean', 'language', 'lexical'])
def test_literal_identity_observations(case):
    def observe(module):
        a, b = pair(module, case)
        return a == b, a != b, hash(a) == hash(b), b in {a}, len({a, b})
    assert observe(rdfcore) == observe(rdflib)


@pytest.mark.parametrize('left', ['URIRef', 'BNode', 'Variable', 'Literal'])
@pytest.mark.parametrize('right', ['URIRef', 'BNode', 'Variable', 'Literal'])
def test_cross_type_identity(left, right):
    def observe(module):
        a, b = getattr(module, left)('urn:x'), getattr(module, right)('urn:x')
        return a == b, a != b, b in {a}, len({a, b})
    assert observe(rdfcore) == observe(rdflib)


@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
@pytest.mark.parametrize('case', ['integer', 'boolean', 'language', 'lexical'])
def test_identity_in_default_and_named_graphs(tmp_path, backend, case):
    def observe(module, store=None, reopen=False):
        dataset = module.Dataset(**({} if store is None else {'store': store}))
        ids = [dataset.default_graph.identifier, module.URIRef('urn:g1'), module.URIRef('urn:g2')]
        a, b = pair(module, case)
        s, p = module.URIRef('urn:s'), module.URIRef('urn:p')
        for identifier in ids:
            graph = dataset.graph(identifier)
            assert graph.add((s, p, a)) is graph
            graph.add((s, p, b))
        dataset.graph(module.URIRef('urn:empty'))
        if reopen:
            dataset.close()
            dataset = module.Dataset(store=module.SQLiteStore(tmp_path / 'identity.sqlite'))
        observations = []
        for identifier in ids:
            graph = dataset.graph(identifier)
            observations.append((len(graph), (s, p, b) in graph))
            assert graph.remove((s, p, b)) is graph
            observations.append((len(graph), (s, p, a) in graph))
        observations.append(len(dataset.graph(module.URIRef('urn:empty'))))
        dataset.close()
        return observations
    store = rdfcore.Memory() if backend == 'memory' else rdfcore.SQLiteStore(tmp_path / 'identity.sqlite')
    assert observe(rdfcore, store, backend == 'sqlite') == observe(rdflib)

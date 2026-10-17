import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('pattern', [None, (None, None, None), (None, None, None, None)])
def test_quads_keyword_and_pattern_lengths(pattern):
    def observe(module):
        dataset = module.Dataset()
        triple = (module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('x'))
        dataset.add(triple)
        try:
            return [tuple(str(term) for term in quad) for quad in dataset.quads(quad=pattern)]
        finally:
            dataset.close()
    assert observe(rdfcore) == observe(rdflib)


def test_dataset_default_serialization_keeps_named_graph():
    for module in (rdflib, rdfcore):
        dataset = module.Dataset()
        dataset.add((module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('x'), module.URIRef('urn:g')))
        result = dataset.serialize()
        parsed = module.Dataset().parse(data=result, format='trig')
        assert len(list(parsed.quads())) == 1
        assert next(parsed.quads())[3] == module.URIRef('urn:g')


@pytest.mark.parametrize('union', [False, True])
@pytest.mark.parametrize('selection', ['implicit', 'named', 'default', 'override'])
def test_dataset_triples_context_selection(union, selection):
    def observe(module):
        dataset = module.Dataset(default_union=union)
        s, p = module.URIRef('urn:s'), module.URIRef('urn:p')
        named = module.URIRef('urn:g')
        dataset.add((s, p, module.Literal('default')))
        dataset.add((s, p, module.Literal('named'), named))
        selector = (None, None, None)
        kwargs = {}
        if selection == 'named':
            selector = (*selector, named)
        elif selection == 'default':
            kwargs['context'] = dataset.default_graph
        elif selection == 'override':
            selector = (*selector, named)
            kwargs['context'] = dataset.default_graph
        return sorted(str(o) for _, _, o in dataset.triples(triple_or_quad=selector, **kwargs))
    assert observe(rdfcore) == observe(rdflib)


def test_dataset_mutation_keyword_arguments():
    for module in (rdflib, rdfcore):
        dataset = module.Dataset()
        key = module.URIRef('urn:g')
        triple = (module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('x'))
        dataset.add_graph(g=key)
        assert dataset.add(triple_or_quad=(*triple, key)) is dataset
        assert len(dataset) == 1
        assert dataset.remove(triple_or_quad=triple) is dataset
        assert len(dataset) == 0
        assert dataset.remove_graph(g=key) is dataset

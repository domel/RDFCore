import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('sqlite', [False, True])
@pytest.mark.parametrize('selector', [False, 0, '', [], 'subjects'])
def test_objects_and_value_selectors(sqlite, selector):
    results = []
    for module in (rdflib, rdfcore):
        options = {'store': rdfcore.SQLiteStore()} if sqlite and module is rdfcore else {}
        graph = module.Graph(**options)
        s, p = module.URIRef('urn:s'), module.URIRef('urn:p')
        graph.add((s, p, module.Literal('v')))
        subject = [s, s] if selector == 'subjects' else selector
        try:
            results.append((list(map(str, graph.objects(subject, p, unique=True))),
                            str(graph.value(subject, p, default='absent'))))
        finally:
            graph.close()
    assert results[0] == results[1]

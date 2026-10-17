import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('uri', ['', 'relative.ttl', 'relative.ttl#part', 'https://e/x#part', 'https://e/x#'])
@pytest.mark.parametrize('defrag', [0, 1])
def test_absolutize(uri, defrag):
    expected = rdflib.Graph().absolutize(uri, defrag)
    actual = rdfcore.Graph().absolutize(uri, defrag)
    assert str(actual) == str(expected)


def test_normalize_variable():
    for module in (rdflib, rdfcore):
        graph = module.Graph()
        assert graph.namespace_manager.normalizeUri(rdfTerm=module.Variable('x')) == '?x'

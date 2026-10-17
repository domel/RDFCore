import pytest

from rdfcore import Graph
from rdfcore.exceptions import BadSyntax


@pytest.mark.parametrize('format', ['turtle', 'trig'])
def test_strict_mode_rejects_literal_subject(format):
    with pytest.raises(BadSyntax):
        Graph().parse(data='"x" <urn:p> <urn:o> .', format=format, strict=True)


def test_decimal_without_integer_part():
    graph = Graph().parse(data='<urn:s> <urn:p> .1 .', format='turtle')
    assert str(next(iter(graph))[2]) == '0.1'

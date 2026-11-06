"""Position checks stay in parsers when low-level Graph.add is permissive.

RDF 1.2 Concepts CR 2026-04-07 §3.1; W3C bad-struct-05/07/15/17,
Turtle/TriG bad-kw-05. Legacy generalized syntax is a separate mode.
"""
import pytest
from rdfcore import Graph, Dataset
from rdfcore.exceptions import BadSyntax


@pytest.mark.parametrize('format', ['turtle', 'turtle12', 'trig', 'trig12'])
@pytest.mark.parametrize('predicate', ['"hello"', '_:predicate', 'true', '42'])
def test_strict_predicate_positions(format, predicate):
    graph = Dataset() if format.startswith('trig') else Graph()
    with pytest.raises(BadSyntax):
        graph.parse(data=f'<urn:s> {predicate} <urn:o> .', format=format, strict=True)
    assert len(graph) == 0


@pytest.mark.parametrize('format', ['turtle12', 'trig12'])
@pytest.mark.parametrize('data', ['"subject" <urn:p> <urn:o> .', '<urn:s> _:predicate <urn:o> .'])
def test_rdf12_position_constraints_cannot_be_disabled(format, data):
    graph = Dataset() if format == 'trig12' else Graph()
    with pytest.raises(BadSyntax):
        graph.parse(data=data, format=format, strict=False)
    assert len(graph) == 0

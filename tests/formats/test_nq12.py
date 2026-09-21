import pytest

from rdfcore import Dataset, Literal, TripleTerm, URIRef
from rdfcore.exceptions import ParserError


def test_nq12_round_trip_named_graph_and_rdf12_terms():
    text = '''VERSION "1.2"
<http://e/s> <http://e/p> "x"@en--rtl <http://e/g> .
<http://e/s> <http://e/q> <<( <http://e/a> <http://e/b> <http://e/c> )>> <http://e/g> .
'''
    dataset = Dataset().parse(data=text, format="nq12")
    assert len(list(dataset.quads())) == 2
    quad = next(quad for quad in dataset.quads() if quad[1] == URIRef("http://e/q"))
    assert isinstance(quad[2], TripleTerm)
    encoded = dataset.serialize(format="nq12")
    assert encoded.startswith('VERSION "1.2"\n')
    assert '"x"@en--rtl' in encoded


def test_nquads11_alias_remains_rdf11():
    with pytest.raises(ParserError):
        Dataset().parse(data='<http://e/s> <http://e/p> "x"@en--rtl <http://e/g> .', format="nquads")


def test_nq12_canonical_omits_version():
    dataset = Dataset().parse(data='<http://e/s> <http://e/p> "x"@en--rtl <http://e/g> .', format="nq12")
    encoded = dataset.serialize(format="nq12", canonical=True)
    assert not encoded.startswith("VERSION")


def test_nq12_enforces_explicit_rdf_version():
    with pytest.raises(ParserError):
        Dataset().parse(data='<http://e/s> <http://e/p> "x"@en--rtl <http://e/g> .', format="nq12", rdf_version="1.1")

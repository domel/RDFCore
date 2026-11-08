"""Native values and immutable lexical identity against RDFLib 7.6.0."""
import pytest
import rdflib
import rdfcore


class OpaqueValue:
    def __str__(self):
        return 'opaque value'


@pytest.mark.parametrize('factory', [dict, list, lambda: {'a': 1}, lambda: [1, 2],
                                     lambda: bytearray(b'hello'), OpaqueValue])
def test_native_literal_values_and_copies(factory):
    for options in ({}, {'datatype': 'urn:custom'},
                    {'datatype': str(rdflib.XSD.string)}, {'lang': 'en'}):
        observations = []
        for module in (rdflib, rdfcore):
            value = factory()
            literal = module.Literal(value, **options)
            copied = module.Literal(literal)
            observations.append((str(literal), type(literal.value).__name__,
                                 literal.value is value, literal.toPython() is value,
                                 copied.value is value, copied.toPython() is value,
                                 literal.language, str(literal.datatype), literal.ill_typed))
            assert literal == copied
            assert hash(literal) == hash(copied)
        assert observations[0] == observations[1]


def test_native_mutation_keeps_lexical_form_and_graph_membership():
    for module in (rdflib, rdfcore):
        value = {'a': 1}
        literal = module.Literal(value)
        lexical, original_hash = str(literal), hash(literal)
        graph = module.Graph()
        triple = module.URIRef('urn:s'), module.URIRef('urn:p'), literal
        graph.add(triple)
        value['a'] = 2
        assert str(literal) == lexical
        assert hash(literal) == original_hash
        assert triple in graph
        assert literal.toPython() is value
        assert literal.toPython() == {'a': 2}


def test_string_bytes_and_none_constructors_keep_their_contract():
    for value in ('hello', b'hello', None):
        observations = []
        for module in (rdflib, rdfcore):
            literal = module.Literal(value)
            native = literal.toPython()
            observations.append((str(literal), type(literal.value).__name__,
                                 native is literal, str(native)))
        assert observations[0] == observations[1]

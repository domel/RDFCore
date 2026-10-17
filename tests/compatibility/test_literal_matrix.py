import warnings

import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('value', ['text', '1', 'TRUE', 'maybe', '', None])
@pytest.mark.parametrize('options', [{}, {'lang': ''}, {'lang': 'en'}, {'lang': 'bad_tag'},
    {'datatype': 'urn:unknown'}, {'datatype': str(rdflib.XSD.boolean)},
    {'datatype': str(rdflib.XSD.integer)}])
@pytest.mark.parametrize('normalize', [False, True])
def test_literal_constructor_observations(value, options, normalize):
    def observe(module):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            try:
                literal = module.Literal(value, normalize=normalize, **options)
                converted = literal.toPython()
                return (str(literal), literal.language, str(literal.datatype) if literal.datatype else None,
                        type(literal.value).__name__, str(literal.value), literal.ill_typed,
                        type(converted).__name__, str(converted))
            except Exception as error:
                return type(error).__name__
    assert observe(rdfcore) == observe(rdflib)

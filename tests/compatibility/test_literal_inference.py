import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('value', [1, 1.5, False, None, b'01'])
@pytest.mark.parametrize('datatype', [None, 'integer', 'string'])
@pytest.mark.parametrize('lang', [None, 'en'])
def test_python_literal_inference(value, datatype, lang):
    def observe(module):
        dt = None if datatype is None else module.XSD[datatype]
        try:
            literal = module.Literal(value, datatype=dt, lang=lang)
            return str(literal), str(literal.datatype), literal.language, type(literal.value).__name__, str(literal.value), literal.ill_typed
        except Exception as error:
            return type(error).__name__
    assert observe(rdfcore) == observe(rdflib)


def test_copy_preserves_lexical_form():
    for module in (rdflib, rdfcore):
        source = module.Literal('01', datatype=module.XSD.integer, normalize=False)
        result = module.Literal(source)
        assert str(result) == '01'
        assert result.value == 1
        assert result.ill_typed is None

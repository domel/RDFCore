import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('lexical,datatype', [
    ('01.00', 'decimal'), ('1e0', 'double'), ('a\tb', 'normalizedString'),
    ('  a\t b\n ', 'token'), ('256', 'unsignedByte'), ('-1', 'nonNegativeInteger'),
    ('2020-01-01Z', 'date'), ('2020-01-01+02:00', 'date'), ('Y Q==', 'base64Binary')])
@pytest.mark.parametrize('normalize', [False, True])
def test_datatype_lexical_and_value_mapping(lexical, datatype, normalize):
    def observe(module):
        result = module.Literal(lexical, datatype=module.XSD[datatype], normalize=normalize)
        return str(result), type(result.value).__name__, str(result.value), result.ill_typed
    assert observe(rdfcore) == observe(rdflib)

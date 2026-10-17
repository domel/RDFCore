import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('attribute,replacement', [('language', 'en'), ('datatype', 'urn:type'),
                                                  ('value', 'changed'), ('ill_typed', True)])
def test_literal_public_metadata_is_readonly(attribute, replacement):
    for module in (rdflib, rdfcore):
        literal = module.Literal('x')
        values = {literal}
        with pytest.raises(AttributeError):
            setattr(literal, attribute, replacement)
        with pytest.raises(AttributeError):
            delattr(literal, attribute)
        assert literal in values

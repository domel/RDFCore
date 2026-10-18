"""A positive and negative raw lexical case for every recognized datatype."""
import pytest

from rdfcore import Literal, RDF, XSD
from rdfcore.datatypes import SUPPORTED_DATATYPES, InvalidLexicalForm, datatype_value, lexical_value
from rdfcore.term import _INTEGER_DATATYPES

CASES = {
    XSD.string: ('text', '\ud800'), XSD.normalizedString: ('a b', 'a\tb'),
    XSD.token: ('a b', 'a  b'), XSD.language: ('en-US', 'en_US'),
    XSD.Name: ('a:b', '1bad'), XSD.NCName: ('name', 'a:b'),
    XSD.NMTOKEN: ('1:a', 'a b'), XSD.anyURI: (' relative uri ', '\0'),
    XSD.boolean: ('true', 'TRUE'), XSD.decimal: ('1.0', '1e2'),
    XSD.float: ('NaN', 'nan'), XSD.double: ('+INF', 'infinity'),
    XSD.hexBinary: ('FF', 'F'), XSD.base64Binary: ('YQ==', 'YR=='),
    XSD.duration: ('P1YT1S', 'P'), XSD.yearMonthDuration: ('P1M', 'P1D'),
    XSD.dayTimeDuration: ('PT1S', 'P1Y'),
    XSD.dateTime: ('0000-01-01T00:00:00', '0000-01-01'),
    XSD.dateTimeStamp: ('0000-01-01T00:00:00Z', '0000-01-01T00:00:00'),
    XSD.date: ('0000-02-29', '0001-02-29'), XSD.time: ('24:00:00', '24:00:01'),
    XSD.gYear: ('0000', '000'), XSD.gYearMonth: ('0000-01', '0000-00'),
    XSD.gMonth: ('--01', '--01--'), XSD.gDay: ('---31', '---32'),
    XSD.gMonthDay: ('--02-29', '--02-30'),
    RDF.JSON: ('null', 'NaN'), RDF.XMLLiteral: ('<a/>', '<a>'),
    RDF.HTML: ('<p>text', '\ud800'),
}
for datatype in _INTEGER_DATATYPES:
    CASES[datatype] = ('-1' if datatype in {str(XSD.negativeInteger), str(XSD.nonPositiveInteger)} else '1', '1_0')


def test_recognized_set_has_explicit_cases():
    assert set(map(str, CASES)) | {str(RDF.langString), str(RDF.dirLangString)} == SUPPORTED_DATATYPES


@pytest.mark.parametrize('datatype', sorted(CASES, key=str))
def test_recognized_lexical_spaces(datatype):
    valid, invalid = CASES[datatype]
    assert hash(lexical_value(valid, datatype)) == hash(lexical_value(valid, datatype))
    with pytest.raises(InvalidLexicalForm):
        lexical_value(invalid, datatype)


@pytest.mark.parametrize('direction', [None, 'ltr', 'rtl'])
def test_language_components_are_required_and_preserved(direction):
    value = datatype_value(Literal('text', lang='EN', direction=direction))
    assert value.key == (('text', 'en') if direction is None else ('text', 'en', direction))
    with pytest.raises(InvalidLexicalForm):
        lexical_value('text', RDF.langString if direction is None else RDF.dirLangString)


@pytest.mark.parametrize('lexical,datatype', [(None, XSD.string), ('text', None), (1, XSD.integer)])
def test_raw_value_api_rejects_wrong_argument_types(lexical, datatype):
    with pytest.raises(TypeError):
        lexical_value(lexical, datatype)


def test_value_keys_are_immutable_and_unknown_types_are_not_invalid():
    from rdfcore.datatypes import UnsupportedDatatype
    value = lexical_value('{"a":[1]}', RDF.JSON)
    original = hash(value)
    with pytest.raises(AttributeError):
        value.key = 'changed'
    assert hash(value) == original
    with pytest.raises(UnsupportedDatatype):
        lexical_value('anything', 'urn:unknown')


@pytest.mark.parametrize('datatype', [RDF.HTML, RDF.XMLLiteral, RDF.JSON])
def test_processing_limits_do_not_report_lexical_invalidity(datatype):
    from rdfcore.datatypes import DatatypeResourceLimit
    text = '['*1200+'0'+']'*1200 if datatype == RDF.JSON else '<div>'*257+'</div>'*257
    with pytest.raises(DatatypeResourceLimit):
        lexical_value(text, datatype)

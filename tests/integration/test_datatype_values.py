"""Concepts CR 2026-04-07 § 5, Appendix A; XSD 1.1 Part 2."""
import sys

import pytest

from rdfcore import Literal, RDF, XSD
from rdfcore.datatypes import InvalidLexicalForm, UnsupportedDatatype, datatype_value, same_value


@pytest.mark.parametrize('datatype,left,right', [
    (XSD.integer, '01', '+1'), (XSD.decimal, '1.00', '1'),
    (XSD.boolean, 'true', '1'), (XSD.hexBinary, 'ff', 'FF'),
    (XSD.base64Binary, 'YQ==', ' YQ== '),
    (RDF.JSON, '{"a":1,"b":2}', '{"b":2,"a":1}'),
    (RDF.XMLLiteral, '<a x="1" y="2"/>', '<a y="2" x="1"></a>'),
])
def test_normative_value_identity_does_not_change_term_identity(datatype, left, right):
    a, b = (Literal(text, datatype=datatype, normalize=False) for text in (left, right))
    assert same_value(a, b) is True
    assert a != b
    assert hash(datatype_value(a)) == hash(datatype_value(b))


@pytest.mark.parametrize('datatype,lexical', [
    (XSD.integer, '1_0'), (XSD.integer, '١'), (XSD.decimal, '1e2'),
    (XSD.boolean, 'TRUE'), (XSD.byte, '128'), (XSD.unsignedByte, '-1'),
    (XSD.double, 'infinity'), (XSD.double, 'nan'),
    (XSD.hexBinary, '0'), (XSD.hexBinary, 'ff ff'),
    (XSD.base64Binary, 'YR=='), (RDF.JSON, '{"x":0,"x":1}'),
    (RDF.XMLLiteral, '<a>'),
])
def test_strict_validation_is_independent_of_legacy_conversion(datatype, lexical):
    literal = Literal(lexical, datatype=datatype, normalize=False)
    with pytest.raises(InvalidLexicalForm):
        datatype_value(literal)
    assert str(literal) == lexical


def test_float32_mapping_avoids_double_rounding():
    a = Literal('1.0000000596046447753906250000000000001', datatype=XSD.float, normalize=False)
    b = Literal('1.00000011920928955078125', datatype=XSD.float, normalize=False)
    assert same_value(a, b) is True
    assert same_value(a, Literal('1', datatype=XSD.float)) is False


@pytest.mark.parametrize('datatype', [XSD.float, XSD.double, RDF.JSON])
def test_signed_zero_identity_is_not_arithmetic_equality(datatype):
    assert not same_value(Literal('0', datatype=datatype), Literal('-0', datatype=datatype))


def test_language_and_direction_are_value_components():
    assert same_value(Literal('x', lang='EN'), Literal('x', lang='en'))
    assert not same_value(Literal('x', lang='en'), Literal('x', lang='fr'))
    assert not same_value(Literal('x', lang='en', direction='ltr'),
                          Literal('x', lang='en', direction='rtl'))


def test_unknown_datatypes_are_explicitly_unsupported():
    with pytest.raises(UnsupportedDatatype):
        datatype_value(Literal('value', datatype='urn:unknown'))


def test_html5_fragment_mapping_and_missing_dependency(monkeypatch):
    a, b = Literal('<P>A<br>B', datatype=RDF.HTML), Literal('<p>A<br/>B</p>', datatype=RDF.HTML)
    assert same_value(a, b)
    monkeypatch.setitem(sys.modules, 'html5rdf', None)
    with pytest.raises(UnsupportedDatatype, match='html'):
        datatype_value(a)


def test_xml_dtd_is_not_a_literal_value():
    literal = Literal('<!DOCTYPE x [<!ENTITY e SYSTEM "file:///not-read">]><x>&e;</x>',
                      datatype=RDF.XMLLiteral)
    with pytest.raises(InvalidLexicalForm):
        datatype_value(literal)


@pytest.mark.parametrize('left,right', [
    (Literal('"text"', datatype=RDF.JSON), Literal('text')),
    (Literal('true', datatype=RDF.JSON), Literal('1', datatype=XSD.boolean)),
    (Literal('0', datatype=RDF.JSON), Literal('0', datatype=XSD.double)),
    (Literal('text', datatype=RDF.HTML), Literal('text', datatype=RDF.XMLLiteral)),
    (Literal('1', datatype=XSD.integer), Literal('1.0', datatype=XSD.decimal)),
])
def test_overlapping_value_spaces(left, right):
    assert same_value(left, right)


def test_value_key_is_independent_of_python_decimal_context():
    from decimal import localcontext
    literal = Literal('1.0000000596046447753906250000000000001', datatype=XSD.float, normalize=False)
    expected = datatype_value(literal)
    with localcontext() as context:
        context.prec = 2
        assert datatype_value(literal) == expected


def test_integer_value_mapping_has_no_python_decimal_digit_limit():
    lexical = '1' + '0' * 5000
    value = datatype_value(Literal(lexical, datatype=XSD.integer, normalize=False))
    assert value.key.numerator == 10**5000


@pytest.mark.parametrize('language', ['en', 'en-Latn-US', 'zh-cmn-Hans-CN',
    'es-419', 'sl-rozaj-biske-1994', 'de-CH-1901', 'en-a-bbb-x-a-ccc',
    'x-private', 'i-klingon', 'en-GB-oed', 'sgn-BE-FR'])
def test_language_value_mapping_accepts_well_formed_bcp47(language):
    assert datatype_value(Literal('text', lang=language)).key[1] == language.lower()


@pytest.mark.parametrize('language', ['a', 'abcdefghi', 'i-invalid', 'en-US-CA',
    'en-Latn-Cyrl', 'en-a', 'en-a-b', 'x', 'en-1234abcdz'])
def test_language_validation_is_an_explicit_normative_extension(language):
    import rdflib
    # Legacy construction stays compatible; strict validation is opt-in.
    assert str(rdflib.Literal('text', lang=language)) == str(Literal('text', lang=language))
    with pytest.raises(InvalidLexicalForm, match='BCP47'):
        datatype_value(Literal('text', lang=language))


@pytest.mark.parametrize('lexical', ['', ' relative path ', '\tvalue\n', 'urn:é', 'http://example.org/%GG'])
def test_xsd_anyuri_uses_identity_mapping_not_url_validation(lexical):
    # XSD 1.1 § 3.3.17 defines a string space, not an IRI parser.
    value = Literal(lexical, datatype=XSD.anyURI, normalize=False)
    assert datatype_value(value).key == lexical
    # XSD 1.1 § 2.2.1 makes distinct primitive value spaces disjoint.
    assert not same_value(value, Literal(lexical))


@pytest.mark.parametrize('left,right', [
    (Literal('1', datatype=XSD.integer), Literal('1', datatype=XSD.double)),
    (Literal('1', datatype=XSD.float), Literal('1', datatype=XSD.double)),
    (Literal('FF', datatype=XSD.hexBinary), Literal('/w==', datatype=XSD.base64Binary)),
])
def test_xsd_primitive_value_identity_is_not_numeric_or_python_equality(left, right):
    assert same_value(left, right) is False


def test_dom_attribute_prefix_is_not_part_of_attribute_equality():
    # DOM § 4.4: Element prefix matters; Attr prefix is not compared.
    a = Literal('<a xmlns:x="urn:x" xmlns:y="urn:x" x:p="1"/>', datatype=RDF.XMLLiteral)
    b = Literal('<a xmlns:x="urn:x" xmlns:y="urn:x" y:p="1"/>', datatype=RDF.XMLLiteral)
    assert same_value(a, b)

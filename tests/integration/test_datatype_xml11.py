"""Concepts CR 2026-04-07 Appendix A.2 and XML 1.1 §§ 2.2, 2.11.

Test XML 1.1 value mapping without changing legacy XML parser behavior.
"""
import pytest

from rdfcore import Literal, RDF
from rdfcore.datatypes import datatype_value, InvalidLexicalForm


def key(text):
    return datatype_value(Literal(text, datatype=RDF.XMLLiteral, normalize=False)).key


@pytest.mark.parametrize('codepoint', [*range(1, 9), 11, 12, *range(14, 32),
                                      *range(0x7F, 0x85), *range(0x86, 0xA0)])
def test_xml11_restricted_characters_are_allowed_only_as_references(codepoint):
    value = key(f'&#x{codepoint:X};')
    assert value == ('fragment', ((3, '#text', chr(codepoint)),))
    assert key(f'&#{codepoint};') == value
    with pytest.raises(InvalidLexicalForm):
        key(chr(codepoint))


@pytest.mark.parametrize('newline', ['\r', '\r\n', '\r\x85', '\x85', '\u2028'])
def test_xml11_line_end_normalization(newline):
    assert key('a'+newline+'b') == key('a\nb')
    assert key('<a x="a'+newline+'b"/>') == key('<a x="a b"/>')


@pytest.mark.parametrize('fragment', [
    '<![CDATA[&#x1;]]>', '<!--&#x1;-->', '<?target &#x1;?>',
])
def test_references_are_not_interpreted_inside_cdata_comments_or_pi(fragment):
    assert '&#x1;' in repr(key(fragment))


def test_restricted_references_in_attributes_and_private_use_collisions():
    value = key('<a x="&#x1;&#xF0000;\U000F0001"/>')
    assert value[1][0][4][0][-1] == '\x01\U000F0000\U000F0001'


@pytest.mark.parametrize('fragment', [
    '<a&#x1;/>', '<a x&#x1;="v"/>', '<a xmlns="urn:x&#x1;"/>',
    '&#0;', '&#xD800;', '&#x110000;', '<!DOCTYPE a><a/>',
])
def test_invalid_xml_is_not_made_valid_by_reference_mapping(fragment):
    with pytest.raises(InvalidLexicalForm):
        key(fragment)


@pytest.mark.parametrize('iri', ['urn:é', 'relative/path', 'https://例え.テスト/p',
    'http://[2001:db8::1]:99999/p', 'http://[v1.a:b]/p', 'urn:x?\ue000'])
def test_namespace_iri_references(iri):
    assert key(f'<a xmlns="{iri}"/>')[1][0][1] == iri


@pytest.mark.parametrize('iri', ['urn:%GG', 'urn:x#two#fragments', '1scheme:path',
    'http://host:bad/path', 'http://user@user@host/path', 'urn:\ue000',
    'http://[not-ipv6]/path', 'urn:x#\ue000'])
def test_invalid_namespace_iri_references(iri):
    with pytest.raises(InvalidLexicalForm):
        key(f'<a xmlns="{iri}"/>')

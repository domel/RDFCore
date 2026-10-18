"""Explicit datatype value identity, separate from RDFLib literal conversion.

Baseline: Concepts CR 2026-04-07 § 5 and Appendix A; XSD 1.1 Part 2
REC 2012-04-05 §§ 3.3.4-5 (ED Concepts checked 2026-10-18).
Only SUPPORTED_DATATYPES are recognized here. General D-entailment is not
implemented. XML uses a guarded DOM parser and an XML 1.1 character adapter.
HTML requires the optional html5rdf package and uses its HTML5 DOM builder.
This module never changes Literal.toPython(), term hashes or graph state.
"""
from __future__ import annotations

from base64 import b64decode, b64encode
from binascii import Error as BinaryError
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import math
import re
from xml.dom import Node, minidom
from xml.parsers import expat

from .term import Literal, _INTEGER_BOUNDS, _INTEGER_DATATYPES, _json_value_key, _python_value
from ._datatype_temporal import TEMPORAL_TYPES, DURATION_TYPES, temporal_key, duration_key

XSD = 'http://www.w3.org/2001/XMLSchema#'
RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
_STRINGS = {'string', 'normalizedString', 'token', 'language', 'Name', 'NCName', 'NMTOKEN', 'anyURI'}
SUPPORTED_DATATYPES = frozenset(
    _INTEGER_DATATYPES | {XSD+n for n in _STRINGS | TEMPORAL_TYPES | DURATION_TYPES | {'boolean', 'decimal', 'float', 'double', 'hexBinary', 'base64Binary'}}
    | {RDF+n for n in ('langString', 'dirLangString', 'JSON', 'XMLLiteral', 'HTML')})
__all__ = ['DatatypeValue', 'InvalidLexicalForm', 'UnsupportedDatatype',
           'DatatypeResourceLimit', 'SUPPORTED_DATATYPES', 'datatype_value', 'lexical_value', 'same_value']


class InvalidLexicalForm(ValueError):
    """The lexical form is outside a recognized datatype's lexical space."""


class UnsupportedDatatype(NotImplementedError):
    """A datatype or value-space comparison is not implemented."""


class DatatypeResourceLimit(ValueError):
    """A processing limit was reached, not a lexical validity verdict."""


@dataclass(frozen=True)
class DatatypeValue:
    """Immutable value key; equality means identity, not arithmetic equality."""
    family: str
    key: object


def _invalid(datatype):
    raise InvalidLexicalForm(f'invalid lexical form for {datatype}')


def _floating(lexical, precision):
    if lexical in {'INF', '+INF', '-INF', 'NaN'}:
        return {'+INF': 'INF'}.get(lexical, lexical)
    if not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', lexical):
        _invalid(XSD + ('float' if precision == 24 else 'double'))
    if precision == 53:
        return float(lexical).hex()
    approximate = float(lexical)
    if math.isinf(approximate) or approximate == 0.0:
        return approximate.hex()
    # Round the decimal rational directly to binary32. Converting through a
    # binary64 intermediate can incorrectly round values near halfway points.
    try:
        decimal = Decimal(lexical)
    except InvalidOperation as exc:
        raise DatatypeResourceLimit('decimal exponent exceeds processing limits') from exc
    sign = -1.0 if decimal.is_signed() else 1.0
    if decimal.is_zero(): return math.copysign(0.0, sign).hex()
    if decimal.adjusted() > 39: return '-inf' if sign < 0 else 'inf'
    if decimal.adjusted() < -46: return math.copysign(0.0, sign).hex()
    value = Fraction(decimal.copy_abs())
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    power = Fraction(2**exponent) if exponent >= 0 else Fraction(1, 2**-exponent)
    if value < power: exponent -= 1
    step = max(-149, exponent - 23)
    scaled = value / (2**step) if step >= 0 else value * (2**-step)
    rounded, remainder = divmod(scaled.numerator, scaled.denominator)
    twice = 2 * remainder
    if twice > scaled.denominator or (twice == scaled.denominator and rounded % 2):
        rounded += 1
    if rounded == 2**24:
        rounded //= 2
        step += 1
    if step > 104: return '-inf' if sign < 0 else 'inf'
    return math.copysign(math.ldexp(rounded, step), sign).hex()


def _integer(lexical):
    # int(text) has a configurable digit limit on Python 3.11+. Do not change
    # process-global settings or classify a valid arbitrary-size integer as bad.
    sign = -1 if lexical.startswith('-') else 1
    digits = lexical.lstrip('+-')
    value = 0
    for index in range(0, len(digits), 9):
        chunk = digits[index:index+9]
        value = value * 10**len(chunk) + int(chunk)
    return sign * value


def _dom_key(node, depth=0, restore=None):
    if depth > 256:
        raise DatatypeResourceLimit('markup nesting exceeds 256')
    if node.nodeType == Node.ELEMENT_NODE:
        def clean(value):
            return value.translate(restore) if restore is not None else value
        if restore is not None:
            from .plugins.parsers.rdfxml import is_ncname
            from ._iri_reference import is_iri_reference
            names = [node.localName, node.prefix] + [name for a in node.attributes.values()
                                                    for name in (a.localName or a.name, a.prefix)]
            if any(name and not is_ncname(clean(name)) for name in names):
                _invalid(RDF+'XMLLiteral')
            namespace_values = [node.namespaceURI or '']
            namespace_values += [a.value for a in node.attributes.values()
                                 if a.namespaceURI == 'http://www.w3.org/2000/xmlns/']
            if any(not is_iri_reference(clean(ns)) for ns in namespace_values):
                _invalid(RDF+'XMLLiteral')
        attributes = tuple(sorted((clean(a.namespaceURI or ''), clean(a.localName or a.name), clean(a.value))
                                  for a in node.attributes.values()))
        return ('element', clean(node.namespaceURI or ''), clean(node.prefix or ''), clean(node.localName),
                attributes, tuple(_dom_key(c, depth+1, restore) for c in node.childNodes))
    if node.nodeType in (Node.DOCUMENT_NODE, Node.DOCUMENT_FRAGMENT_NODE):
        return ('fragment', tuple(_dom_key(c, depth+1, restore) for c in node.childNodes))
    value = node.nodeValue
    if restore is not None and value is not None: value = value.translate(restore)
    return (node.nodeType, node.nodeName, value)


def _markup(lexical, html):
    if html:
        try:
            import html5rdf
        except ImportError as exc:
            raise UnsupportedDatatype('rdf:HTML requires installation of rdfcore[html]') from exc
        dom = html5rdf.parseFragment(lexical, treebuilder='dom')
        try:
            dom.normalize()
            return _dom_key(dom)
        finally:
            dom.unlink()
    from ._datatype_xml import xml11_source
    lexical, restore = xml11_source(lexical)
    parser = expat.ParserCreate()
    def forbid(*args):
        _invalid(RDF+'XMLLiteral')
    parser.StartDoctypeDeclHandler = forbid
    parser.ExternalEntityRefHandler = forbid
    wrapped = '<rdfcore-fragment>'+lexical+'</rdfcore-fragment>'
    depth = 0
    def start(*args):
        nonlocal depth
        depth += 1
        if depth > 257:
            raise DatatypeResourceLimit('markup nesting exceeds 256')
    def end(*args):
        nonlocal depth
        depth -= 1
    parser.StartElementHandler, parser.EndElementHandler = start, end
    try:
        parser.Parse(wrapped, True)
        dom = minidom.parseString(wrapped)
    except expat.ExpatError as exc:
        raise InvalidLexicalForm('invalid rdf:XMLLiteral fragment') from exc
    try:
        dom.normalize()
        return ('fragment', tuple(_dom_key(c, restore=restore) for c in dom.documentElement.childNodes))
    finally:
        dom.unlink()


def datatype_value(literal: Literal) -> DatatypeValue:
    """Validate an immutable lexical form and return its immutable value key.

    Unknown types raise UnsupportedDatatype, not InvalidLexicalForm. For
    validation of original input, construct Literal(..., normalize=False).
    Legacy constructor normalization may already have changed the input.
    """
    if not isinstance(literal, Literal): raise TypeError('expected a Literal')
    return _value(str(literal), str(literal.datatype or XSD+'string'),
                  literal.language, literal.direction)


def lexical_value(lexical: str, datatype: str) -> DatatypeValue:
    """Validate original typed lexical input without constructor normalization.

    Language-bearing values require datatype_value(Literal(..., lang=...)).
    No RDF term is constructed or mutated by this function.
    """
    if not isinstance(lexical, str) or not isinstance(datatype, str):
        raise TypeError('lexical form and datatype must be strings')
    return _value(str(lexical), str(datatype))


def _value(lexical, datatype, language=None, direction=None):
    if any(0xD800 <= ord(c) <= 0xDFFF for c in lexical):
        raise InvalidLexicalForm('RDF strings cannot contain surrogate code points')
    if language:
        from ._language import well_formed_language_tag
        if not well_formed_language_tag(language):
            raise InvalidLexicalForm('language tag is not BCP47 well-formed')
        if direction:
            return DatatypeValue('dirLangString', (lexical, language.lower(), direction))
        return DatatypeValue('langString', (lexical, language.lower()))
    if datatype not in SUPPORTED_DATATYPES: raise UnsupportedDatatype(datatype)
    try:
        if datatype == RDF+'JSON':
            value = _python_value(lexical, datatype)
            if isinstance(value, str): return DatatypeValue('string', value)
            if isinstance(value, bool): return DatatypeValue('boolean', value)
            if isinstance(value, float): return DatatypeValue('double', value.hex())
            return DatatypeValue('JSON', _json_value_key(value))
        if datatype in {RDF+'HTML', RDF+'XMLLiteral'}:
            return DatatypeValue('markup', _markup(lexical, datatype == RDF+'HTML'))
        if datatype in {RDF+'langString', RDF+'dirLangString'}:
            _invalid(datatype)  # These require language/direction components.
        name = datatype[len(XSD):]
        if name in TEMPORAL_TYPES:
            return DatatypeValue('temporal', temporal_key(lexical, name))
        if name in DURATION_TYPES:
            return DatatypeValue('duration', duration_key(lexical, name))
        if name in _STRINGS:
            # XSD's XML-character string spaces use XML 1.1 here, consistently
            # with the selected Concepts XMLLiteral baseline.
            if any(ord(c) in (0, 0xFFFE, 0xFFFF) for c in lexical): _invalid(datatype)
            if name == 'normalizedString' and any(c in lexical for c in '\r\n\t'): _invalid(datatype)
            if name not in {'string', 'normalizedString', 'anyURI'}:
                if lexical != lexical.strip(' \t\r\n') or re.search(r'  |[\t\r\n]', lexical): _invalid(datatype)
            if name == 'language' and not re.fullmatch(r'[A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})*', lexical): _invalid(datatype)
            if name in {'Name', 'NCName', 'NMTOKEN'}:
                from .plugins.parsers.rdfxml import is_ncname
                candidate = lexical.replace(':', '_') if name != 'NCName' else lexical
                if not is_ncname(('_'+candidate) if name == 'NMTOKEN' else candidate) or not lexical: _invalid(datatype)
            return DatatypeValue('anyURI' if name == 'anyURI' else 'string', lexical)
        if datatype in _INTEGER_DATATYPES:
            if not re.fullmatch(r'[+-]?[0-9]+', lexical): _invalid(datatype)
            value = _integer(lexical)
            lower, upper = _INTEGER_BOUNDS.get(datatype, (None, None))
            if (lower is not None and value < lower) or (upper is not None and value > upper): _invalid(datatype)
            return DatatypeValue('numeric', Fraction(value))
        if name == 'decimal':
            if not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)', lexical): _invalid(datatype)
            return DatatypeValue('numeric', Fraction(Decimal(lexical)))
        if name == 'boolean':
            if lexical not in {'true', 'false', '1', '0'}: _invalid(datatype)
            return DatatypeValue('boolean', lexical in {'true', '1'})
        if name in {'float', 'double'}:
            key = _floating(lexical, 24 if name == 'float' else 53)
            key = {'INF': 'inf', '-INF': '-inf', 'NaN': 'nan'}.get(key, key)
            return DatatypeValue(name, key)
        if name == 'hexBinary':
            if not re.fullmatch(r'(?:[0-9A-Fa-f]{2})*', lexical): _invalid(datatype)
            return DatatypeValue('hexBinary', bytes.fromhex(lexical))
        if name == 'base64Binary':
            compact = re.sub(r'[ \t\r\n]', '', lexical)
            value = b64decode(compact, validate=True)
            if b64encode(value).decode('ascii') != compact: _invalid(datatype)
            return DatatypeValue('base64Binary', value)
    except (InvalidOperation, BinaryError, UnicodeError) as exc:
        raise InvalidLexicalForm(f'invalid lexical form for {datatype}') from exc
    except RecursionError as exc:
        raise DatatypeResourceLimit('datatype nesting exceeds processing limits') from exc
    except ValueError as exc:
        if isinstance(exc, (InvalidLexicalForm, DatatypeResourceLimit)): raise
        raise InvalidLexicalForm(f'invalid lexical form for {datatype}') from exc
    raise UnsupportedDatatype(datatype)


def same_value(left: Literal, right: Literal) -> bool:
    """Compare supported value identities, not RDF term or numeric equality.

    XSD primitive spaces remain disjoint (§ 2.2.1); derived types share
    their primitive's space. No datatype entailment or inference is performed.
    """
    a, b = datatype_value(left), datatype_value(right)
    return a == b

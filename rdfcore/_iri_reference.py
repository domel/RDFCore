"""RFC 3987 § 2.2 syntax for XML namespace IRI references.

No resolution, normalization, scheme-specific validation or network access.
This is intentionally separate from RDFLib-compatible URIRef construction.
"""
from ipaddress import IPv6Address
import re

_PARTS = re.compile(r'(?:(?P<scheme>[A-Za-z][A-Za-z0-9+.-]*):)?'
                    r'(?://(?P<authority>[^/?#]*))?(?P<path>[^?#]*)'
                    r'(?:\?(?P<query>[^#]*))?(?:#(?P<fragment>.*))?', re.S)
_UNRESERVED = frozenset('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~')
_SUBDELIMS = frozenset("!$&'()*+,;=")
_HEX = frozenset('0123456789abcdefABCDEF')


def _ucschar(cp):
    return (0xA0 <= cp <= 0xD7FF or 0xF900 <= cp <= 0xFDCF
            or 0xFDF0 <= cp <= 0xFFEF
            or (0x10000 <= cp <= 0xDFFFD and cp & 0xFFFF <= 0xFFFD)
            or 0xE1000 <= cp <= 0xEFFFD)


def _characters(text, extra=frozenset(), private=False):
    position = 0
    while position < len(text):
        char = text[position]
        if char == '%':
            if position+2 >= len(text) or any(c not in _HEX for c in text[position+1:position+3]):
                return False
            position += 3
            continue
        cp = ord(char)
        if not (char in _UNRESERVED or char in _SUBDELIMS or char in extra or _ucschar(cp)
                or (private and (0xE000 <= cp <= 0xF8FF or 0xF0000 <= cp <= 0xFFFFD or 0x100000 <= cp <= 0x10FFFD))):
            return False
        position += 1
    return True


def _authority(value):
    if value.count('@') > 1: return False
    if '@' in value:
        user, value = value.split('@')
        if not _characters(user, {':'}): return False
    if value.startswith('['):
        end = value.find(']')
        if end < 0: return False
        host, port = value[1:end], value[end+1:]
        if port and (not port.startswith(':') or not re.fullmatch(r'[0-9]*', port[1:])):
            return False
        if re.fullmatch(r'[vV][0-9A-Fa-f]+\.[A-Za-z0-9._~!$&\x27()*+,;=:-]+', host):
            return True
        if '%' in host: return False  # Zone identifiers are not RFC 3987 IP-literal syntax.
        try:
            IPv6Address(host)
            return True
        except ValueError:
            return False
    host, separator, port = value.partition(':')
    return _characters(host) and (not separator or re.fullmatch(r'[0-9]*', port) is not None)


def is_iri_reference(value):
    match = _PARTS.fullmatch(value)
    if match is None: return False
    parts = match.groupdict()
    if parts['authority'] is not None and not _authority(parts['authority']): return False
    path = parts['path']
    if not parts['scheme'] and not path.startswith('/') and ':' in path.split('/', 1)[0]: return False
    return (_characters(path, {'/', ':', '@'})
            and _characters(parts['query'] or '', {'/', '?', ':', '@'}, private=True)
            and _characters(parts['fragment'] or '', {'/', '?', ':', '@'}))

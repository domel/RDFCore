"""XML 1.1 fragment character adapter for the guarded stdlib DOM parser.

XML 1.1 Second Edition §§ 2.2 and 2.11. No DTDs or new entities are
introduced. Restricted references use collision-free private-use characters
above the XML Name range, then are restored in DOM value keys, never markup.
"""
from itertools import chain
import re

_REFERENCES = re.compile(r'&#(x[0-9A-Fa-f]+|[0-9]+);')
_TOKENS = re.compile(r'<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|&#(?:x[0-9A-Fa-f]+|[0-9]+);', re.S)


def _codepoint(reference):
    value = reference[3:-1] if reference.startswith('&#x') else reference[2:-1]
    value = value.lstrip('0') or '0'
    if len(value) > 8: return 0x110000
    return int(value, 16 if reference.startswith('&#x') else 10)


def _restricted(codepoint):
    return (1 <= codepoint <= 8 or codepoint in (11, 12)
            or 14 <= codepoint <= 31 or 0x7F <= codepoint <= 0x84
            or 0x86 <= codepoint <= 0x9F)


def xml11_source(lexical):
    if any(ord(c) == 0 or _restricted(ord(c)) for c in lexical):
        raise ValueError('XML 1.1 restricted characters require character references')
    lexical = (lexical.replace('\r\n', '\n').replace('\r\x85', '\n')
               .replace('\r', '\n').replace('\x85', '\n').replace('\u2028', '\n'))
    occupied = set(map(ord, lexical))
    occupied.update(_codepoint(match.group()) for match in _REFERENCES.finditer(lexical))
    candidates = (cp for cp in chain(range(0xF0000, 0xFFFFE), range(0x100000, 0x10FFFE)) if cp not in occupied)
    replacements, restore = {}, {}

    def substitute(match):
        token = match.group()
        if not token.startswith('&#'): return token
        cp = _codepoint(token)
        if not 1 <= cp <= 31 or cp in (9, 10, 13): return token
        if cp not in replacements:
            try:
                temporary = next(candidates)
            except StopIteration as exc:
                # Not a lexical-invalid verdict: all available placeholders
                # occur in this input, so this adapter cannot process it.
                from .datatypes import DatatypeResourceLimit
                raise DatatypeResourceLimit('XML reference adapter capacity exceeded') from exc
            replacements[cp] = chr(temporary)
            restore[temporary] = chr(cp)
        return replacements[cp]
    return _TOKENS.sub(substitute, lexical), restore

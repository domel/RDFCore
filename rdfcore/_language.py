"""BCP47 well-formedness (RFC 5646 §§ 2.1, 2.2.9), not IANA validity."""
import re

_GRANDFATHERED = frozenset('''en-gb-oed i-ami i-bnn i-default i-enochian
i-hak i-klingon i-lux i-mingo i-navajo i-pwn i-tao i-tay i-tsu
sgn-be-fr sgn-be-nl sgn-ch-de art-lojban cel-gaulish no-bok no-nyn
zh-guoyu zh-hakka zh-min zh-min-nan zh-xiang'''.split())
_TAG = re.compile(
    r'(?:[a-z]{2,3}(?:-[a-z]{3}){0,3}|[a-z]{4}|[a-z]{5,8})'
    r'(?:-[a-z]{4})?(?:-(?:[a-z]{2}|[0-9]{3}))?'
    r'(?:-(?:[a-z0-9]{5,8}|[0-9][a-z0-9]{3}))*'
    r'(?:-[0-9a-wy-z](?:-[a-z0-9]{2,8})+)*'
    r'(?:-x(?:-[a-z0-9]{1,8})+)?', re.I | re.A)
_PRIVATE = re.compile(r'x(?:-[a-z0-9]{1,8})+', re.I | re.A)


def well_formed_language_tag(value):
    """Check the RFC's ABNF, without imposing registry validity or prefixes."""
    return isinstance(value, str) and (value.lower() in _GRANDFATHERED
            or _PRIVATE.fullmatch(value) is not None or _TAG.fullmatch(value) is not None)

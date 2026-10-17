"""Literal ordering helpers for the default RDFLib 7.6.0 collation.

These functions deliberately preserve partial ordering and NotImplemented
results. They rely on Literal's parsed value and value equality (``eq``);
they neither parse lexical forms nor alter term identity. RDFLib's optional
global DAWG_LITERAL_COLLATION switch is outside this default collation.
"""

from datetime import datetime, time


_XSD = "http://www.w3.org/2001/XMLSchema#"
_STRING = _XSD + "string"
_NUMERIC = frozenset(_XSD + name for name in (
    "integer", "decimal", "double", "float", "byte", "int", "long",
    "negativeInteger", "nonNegativeInteger", "nonPositiveInteger",
    "positiveInteger", "short", "unsignedByte", "unsignedInt",
    "unsignedLong", "unsignedShort",
))


def _time_key(value):
    # RDFLib places naive temporal values before aware ones. Within either
    # group Python supplies the chronological comparison, including offsets.
    offset = value.utcoffset() if type(value) is datetime else (
        value.tzinfo.utcoffset(None) if value.tzinfo is not None else None
    )
    return offset is not None, value


def literal_gt(self, other):
    """Compare parsed values, then datatype/language/lexical fallbacks."""
    # Deferred imports allow term.py to import these helpers while defining
    # Literal, without a circular module initialization dependency.
    from .term import Literal, Node

    if other is None:
        return True
    if not isinstance(other, Literal):
        return True if isinstance(other, Node) else NotImplemented

    left_type = str(self.datatype) if self.datatype is not None else _STRING
    right_type = str(other.datatype) if other.datatype is not None else _STRING
    have_values = self.value is not None and other.value is not None
    if (left_type in _NUMERIC and right_type in _NUMERIC and have_values
            and not self.ill_typed and not other.ill_typed):
        return self.value > other.value

    if left_type != right_type:
        return left_type > right_type
    if self.language != other.language:
        return bool(self.language) and (
            not other.language or self.language > other.language
        )
    if have_values:
        if type(self.value) in (datetime, time):
            return _time_key(self.value) > _time_key(other.value)
        try:
            return self.value > other.value
        except TypeError:
            # Unknown/unorderable values still have a lexical ordering.
            pass
    if str(self) != str(other):
        return str(self) > str(other)
    # Equal lexical forms with missing parsed values distinguish a plain
    # literal from an explicitly typed xsd:string literal.
    return self.datatype is not None and other.datatype is None


def literal_lt(self, other):
    """Preserve RDFLib's asymmetric less-than and unknown-value handling."""
    from .term import Literal, Node

    if other is None:
        return False
    if isinstance(other, Literal):
        try:
            return not literal_gt(self, other) and not self.eq(other)
        except TypeError:
            return NotImplemented
    return False if isinstance(other, Node) else NotImplemented


def _inclusive(self, other, strict):
    result = strict(self, other)
    # Match the interpreter-dependent oracle behavior: bool(NotImplemented)
    # warns on older Python versions and raises TypeError on Python 3.14.
    if result:
        return True
    try:
        return self.eq(other)
    except TypeError:
        return NotImplemented


def literal_le(self, other):
    return _inclusive(self, other, literal_lt)


def literal_ge(self, other):
    return _inclusive(self, other, literal_gt)


def literal_bool(self):
    """Use the Python value when available, otherwise lexical nonemptiness."""
    return bool(self.value) if self.value is not None else len(self) != 0

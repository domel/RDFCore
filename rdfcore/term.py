"""RDF 1.1 term types compatible with the core RDFLib API."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from base64 import b64decode
from binascii import Error as BinasciiError, unhexlify
import json
from urllib.parse import urljoin, urlparse
from uuid import uuid4

NORMALIZE_LITERALS = True

_XSD = "http://www.w3.org/2001/XMLSchema#"
_RDF_LANG_STRING = "http://www.w3.org/1999/02/22-rdf-syntax-ns#langString"
_RDF_JSON = "http://www.w3.org/1999/02/22-rdf-syntax-ns#JSON"


class Node(str):
    """Base class for RDF terms represented as strings."""

    def n3(self, namespace_manager=None) -> str:
        return str(self)


Identifier = Node
IdentifiedNode = Node


class URIRef(IdentifiedNode):
    def __new__(cls, value: str, base: str | None = None):
        if base is not None:
            value = urljoin(base, value)
        return str.__new__(cls, value)

    def n3(self, namespace_manager=None) -> str:
        if namespace_manager is not None:
            try:
                return namespace_manager.normalizeUri(self)
            except (AttributeError, KeyError):
                pass
        return f"<{_escape_iri(str(self))}>"

    def de_skolemize(self):
        """Convert an RDF 1.1 skolem URI back to a blank node."""
        path = urlparse(str(self)).path
        marker = "/.well-known/genid/"
        if not path.startswith(marker):
            raise Exception(f"<{self}> is not a skolem URI")
        value = path.split(marker, 1)[1]
        if value.startswith("rdflib/"):
            value = value[len("rdflib/"):]
        if not value:
            raise Exception(f"<{self}> is not a skolem URI")
        return BNode(value=value)


class BNode(IdentifiedNode):
    def __new__(cls, value: str | None = None):
        return str.__new__(cls, value if value is not None else f"{uuid4().hex}")

    def n3(self, namespace_manager=None) -> str:
        return f"_:{self}"

    def skolemize(self, authority=None, basepath=None):
        """Create a deterministic RDF 1.1 skolem URI for this blank node."""
        authority = "https://rdflib.github.io" if authority is None else authority
        basepath = "/.well-known/genid/rdflib/" if basepath is None else basepath
        return URIRef(urljoin(authority, str(basepath) + str(self)))


class Variable(Identifier):
    def __new__(cls, value: str):
        value = str(value)
        if value.startswith("?"):
            value = value[1:]
        return str.__new__(cls, value)

    def n3(self, namespace_manager=None) -> str:
        return f"?{self}"


class TripleTerm:
    """An RDF 1.2 embedded triple term.

    It deliberately is not a ``str`` subclass: its identity is the three
    component terms, not a presentation string.
    """

    __slots__ = ("subject", "predicate", "object", "_hash")

    def __init__(self, subject, predicate, object):
        if not isinstance(subject, (URIRef, BNode)):
            raise TypeError("TripleTerm subject must be a URIRef or BNode")
        if not isinstance(predicate, URIRef):
            raise TypeError("TripleTerm predicate must be a URIRef")
        if not isinstance(object, (URIRef, BNode, Literal, TripleTerm)):
            raise TypeError("TripleTerm object must be an RDF term")
        self.subject = subject
        self.predicate = predicate
        self.object = object
        self._hash = hash((subject, predicate, object))

    def __setattr__(self, name, value):
        if hasattr(self, name):
            raise AttributeError("TripleTerm is immutable")
        object.__setattr__(self, name, value)

    def __iter__(self):
        return iter((self.subject, self.predicate, self.object))

    def __len__(self):
        return 3

    def __getitem__(self, index):
        return (self.subject, self.predicate, self.object)[index]

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return isinstance(other, TripleTerm) and tuple(self) == tuple(other)

    def __repr__(self):
        return f"TripleTerm({self.subject!r}, {self.predicate!r}, {self.object!r})"

    def n3(self, namespace_manager=None):
        return "<<( " + " ".join(term.n3(namespace_manager) if hasattr(term, "n3") else str(term) for term in self) + " )>>"


class Literal(Identifier):
    def __new__(
        cls,
        lexical_or_value,
        lang: str | None = None,
        datatype: str | URIRef | None = None,
        normalize: bool | None = None,
        *,
        direction: str | None = None,
    ):
        if direction not in (None, "ltr", "rtl"):
            raise ValueError("direction must be 'ltr', 'rtl', or None")
        if lang is not None and datatype is not None:
            raise TypeError("A literal cannot have both language and datatype")
        if isinstance(lexical_or_value, Literal):
            source = lexical_or_value
            value, lexical, inferred = source.value, str(source), source.datatype
            if lang is None and datatype is None:
                lang = source.language
            if direction is None:
                direction = source.direction
        else:
            value, lexical, inferred = _literal_parts(lexical_or_value)
        if direction is not None and not lang:
            raise TypeError("a directional literal requires a non-empty language tag")
        if direction is not None and datatype is not None:
            raise TypeError("a directional literal cannot have an explicit datatype")
        datatype = URIRef(datatype) if datatype is not None else inferred
        if normalize is None:
            normalize = NORMALIZE_LITERALS
        ill_typed = None
        if datatype is not None:
            try:
                value = _python_value(lexical, datatype)
                if (
                    (
                        isinstance(lexical_or_value, str)
                        or isinstance(lexical_or_value, Literal)
                    )
                    and str(datatype) in _VALIDATED_DATATYPES
                ):
                    ill_typed = False
                if normalize:
                    lexical = _normalize_lexical(lexical, datatype)
            except (ValueError, ArithmeticError):
                ill_typed = True
                value = None
        obj = str.__new__(cls, lexical)
        obj.language = lang
        obj.direction = direction
        obj.datatype = datatype if lang is None else None
        obj.value = value
        obj.ill_typed = ill_typed
        return obj

    def __hash__(self):
        return hash((str(self), self.language.lower() if self.language else None, self.direction, self.datatype))

    def __eq__(self, other):
        if not isinstance(other, Literal):
            return False
        return (
            str(self) == str(other)
            and (self.language or "").lower() == (other.language or "").lower()
            and self.direction == other.direction
            and self.datatype == other.datatype
        )

    def __ne__(self, other):
        return not self == other

    def n3(self, namespace_manager=None) -> str:
        text = '"' + _escape_literal(str(self)) + '"'
        if self.language is not None:
            suffix = "@" + self.language
            if self.direction is not None:
                suffix += "--" + self.direction
            return text + suffix
        if self.datatype is not None:
            datatype = self.datatype.n3(namespace_manager) if hasattr(self.datatype, "n3") else f"<{self.datatype}>"
            return text + "^^" + datatype
        return text

    def toPython(self):
        return self.value

    def eq(self, other):
        return self == other

    def neq(self, other):
        return not self.eq(other)

    def normalize(self):
        if self.datatype is None:
            return self
        return Literal(str(self), datatype=self.datatype, normalize=True)


def _literal_parts(value):
    if isinstance(value, bool):
        return value, ("true" if value else "false"), URIRef(_XSD + "boolean")
    if isinstance(value, int):
        return value, str(value), URIRef(_XSD + "integer")
    if isinstance(value, float):
        return value, repr(value), URIRef(_XSD + "double")
    if isinstance(value, Decimal):
        return value, str(value), URIRef(_XSD + "decimal")
    if isinstance(value, datetime):
        return value, value.isoformat(), URIRef(_XSD + "dateTime")
    if isinstance(value, date):
        return value, value.isoformat(), URIRef(_XSD + "date")
    if isinstance(value, time):
        return value, value.isoformat(), URIRef(_XSD + "time")
    return str(value), str(value), None


def _normalize_lexical(lexical, datatype):
    if str(datatype) in _INTEGER_DATATYPES:
        return str(int(lexical))
    if str(datatype) == _XSD + "boolean":
        return "true" if lexical in ("true", "1") else "false" if lexical in ("false", "0") else lexical
    return lexical


def _python_value(lexical, datatype):
    name = str(datatype)
    try:
        if name in _STRING_DATATYPES: return lexical
        if name == _RDF_JSON:
            value = json.loads(
                lexical,
                parse_int=float,
                parse_float=float,
                parse_constant=_reject_json_constant,
                object_pairs_hook=_json_object,
            )
            _reject_surrogates(value)
            return value
        if name in _INTEGER_DATATYPES:
            value = int(lexical)
            lower, upper = _INTEGER_BOUNDS.get(name, (None, None))
            if lower is not None and value < lower:
                raise ValueError(lexical)
            if upper is not None and value > upper:
                raise ValueError(lexical)
            return value
        if name == _XSD + "boolean":
            if lexical not in ("true", "false", "1", "0"):
                raise ValueError(lexical)
            return lexical in ("true", "1")
        if name in (_XSD + "double", _XSD + "float"): return float(lexical)
        if name == _XSD + "decimal": return Decimal(lexical)
        if name == _XSD + "dateTime": return datetime.fromisoformat(lexical.replace("Z", "+00:00"))
        if name == _XSD + "date": return date.fromisoformat(lexical)
        if name == _XSD + "time": return time.fromisoformat(lexical.replace("Z", "+00:00"))
        if name == _XSD + "hexBinary": return unhexlify(lexical)
        if name == _XSD + "base64Binary": return b64decode(lexical, validate=True)
    except (ValueError, ArithmeticError, BinasciiError):
        raise
    return lexical


_STRING_DATATYPES = {
    _XSD + name for name in (
        "string", "normalizedString", "token", "language", "Name", "NCName",
        "NMTOKEN", "anyURI",
    )
}
_INTEGER_DATATYPES = {
    _XSD + name for name in (
        "integer", "long", "int", "short", "byte", "nonPositiveInteger",
        "negativeInteger", "nonNegativeInteger", "positiveInteger",
        "unsignedLong", "unsignedInt", "unsignedShort", "unsignedByte",
    )
}
_INTEGER_BOUNDS = {
    _XSD + "long": (-(2**63), 2**63 - 1),
    _XSD + "int": (-(2**31), 2**31 - 1),
    _XSD + "short": (-(2**15), 2**15 - 1),
    _XSD + "byte": (-(2**7), 2**7 - 1),
    _XSD + "nonPositiveInteger": (None, 0),
    _XSD + "negativeInteger": (None, -1),
    _XSD + "nonNegativeInteger": (0, None),
    _XSD + "positiveInteger": (1, None),
    _XSD + "unsignedLong": (0, 2**64 - 1),
    _XSD + "unsignedInt": (0, 2**32 - 1),
    _XSD + "unsignedShort": (0, 2**16 - 1),
    _XSD + "unsignedByte": (0, 2**8 - 1),
}
_VALIDATED_DATATYPES = _STRING_DATATYPES | _INTEGER_DATATYPES | {
    _XSD + "boolean",
    _XSD + "double",
    _XSD + "float",
    _XSD + "decimal",
    _XSD + "dateTime",
    _XSD + "date",
    _XSD + "time",
    _XSD + "hexBinary",
    _XSD + "base64Binary",
    _RDF_JSON,
}


def _reject_json_constant(value):
    raise ValueError(value)


def _json_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON object member: {key!r}")
        value[key] = item
    return value


def _reject_surrogates(value):
    if isinstance(value, str):
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ValueError("JSON strings must not contain surrogate code points")
    elif isinstance(value, list):
        for item in value:
            _reject_surrogates(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            _reject_surrogates(key)
            _reject_surrogates(item)


def _escape_literal(value):
    simple = {"\\": "\\\\", '"': '\\"', "\t": "\\t", "\b": "\\b", "\n": "\\n", "\r": "\\r", "\f": "\\f"}
    return "".join(simple.get(char, _unicode_escape(char) if ord(char) < 0x20 else char) for char in value)


def _escape_iri(value):
    return "".join(
        _unicode_escape(char) if ord(char) <= 0x20 or char in '<>"{}|^`\\' else char
        for char in value
    )


def _unicode_escape(char):
    return f"\\u{ord(char):04X}" if ord(char) <= 0xFFFF else f"\\U{ord(char):08X}"

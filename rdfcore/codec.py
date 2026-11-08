"""Version-one storage representation of RDF terms."""

import io
import json
import pickle

from .term import BNode, Genid, RDFLibGenid, Literal, TripleTerm, URIRef, Variable


# Structural limits, not a bound on the byte size of a literal or a pickle.
MAX_DEPTH = 128


def load_json(data):
    """Read data-only JSON, rejecting excessive nesting before parsing."""
    raw = bytes(data)
    depth = 0
    quoted = escaped = False
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            if depth > MAX_DEPTH + 4:
                raise ValueError("stored RDF nesting limit exceeded")
        elif byte in (93, 125):
            depth -= 1
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeError, RecursionError) as error:
        raise ValueError("invalid stored RDF JSON") from error


def encode(term, *, canonical=True, preserve_state=False, preserve_diagnostics=False):
    from .graph import Graph

    def pack(value, depth=0):
        if depth > MAX_DEPTH:
            raise ValueError("stored RDF nesting limit exceeded")
        if isinstance(value, Graph):
            return ["graph", pack(value.identifier, depth + 1)]
        if value is None:
            return ["none"]
        if isinstance(value, Literal):
            language = (
                value.language.lower()
                if canonical and value.language
                else value.language
            )
            parts = [
                "literal",
                str(value),
                language,
                str(value.datatype) if value.datatype is not None else None,
                value.direction,
            ]
            if preserve_state or preserve_diagnostics:
                return [
                    "literal-state",
                    parts,
                    value.ill_typed,
                    ["lexical"] if preserve_diagnostics else _pack_native(value.value),
                ]
            return parts
        if isinstance(value, TripleTerm):
            return ["triple", *(pack(item, depth + 1) for item in value)]
        for cls, tag in (
            (RDFLibGenid, "rdflib-genid"),
            (Genid, "genid"),
            (URIRef, "uri"),
            (BNode, "blank"),
            (Variable, "variable"),
        ):
            if isinstance(value, cls):
                return [tag, str(value)]
        raise TypeError("unsupported stored RDF term")

    return json.dumps(pack(term), ensure_ascii=True, separators=(",", ":")).encode(
        "ascii"
    )


def decode_value(value):
    """Validate an already parsed JSON term tree."""

    def unpack(value, depth=0):
        if depth > MAX_DEPTH:
            raise ValueError("stored RDF nesting limit exceeded")
        if not isinstance(value, list) or not value:
            raise ValueError("invalid stored RDF term")
        tag, *parts = value
        if not isinstance(tag, str):
            raise ValueError("invalid stored RDF tag")
        if tag == "literal-state" and len(parts) == 3:
            if not isinstance(parts[0], list) or not parts[0] or parts[0][0] != "literal":
                raise ValueError("invalid stored literal state")
            literal = unpack(parts[0], depth)
            if not isinstance(literal, Literal) or not (
                parts[1] is None or type(parts[1]) is bool
            ):
                raise ValueError("invalid stored literal state")
            native = _unpack_native(parts[2], literal.value)
            object.__setattr__(literal, "value", native)
            object.__setattr__(literal, "ill_typed", parts[1])
            return literal
        if tag == "graph" and len(parts) == 1:
            from .graph import Graph

            identifier = unpack(parts[0], depth + 1)
            if not isinstance(identifier, (URIRef, BNode)):
                raise ValueError("invalid stored graph identifier")
            return Graph(identifier=identifier)
        if tag == "none" and not parts:
            return None
        classes = {
            "uri": URIRef,
            "blank": BNode,
            "variable": Variable,
            "genid": Genid,
            "rdflib-genid": RDFLibGenid,
        }
        if tag in classes and len(parts) == 1 and isinstance(parts[0], str):
            return classes[tag](parts[0])
        if tag == "literal" and len(parts) == 4:
            lexical, language, datatype, direction = parts
            if not isinstance(lexical, str) or any(
                x is not None and not isinstance(x, str) for x in parts[1:]
            ):
                raise ValueError("invalid stored literal")
            return Literal(
                lexical,
                lang=language,
                datatype=datatype,
                direction=direction,
                normalize=False,
            )
        if tag == "triple" and len(parts) == 3:
            return TripleTerm(*(unpack(part, depth + 1) for part in parts))
        raise ValueError("invalid stored RDF term")

    try:
        return unpack(value)
    except (TypeError, RecursionError, ArithmeticError) as error:
        raise ValueError("invalid stored RDF term") from error


def decode(data):
    return decode_value(load_json(data))


class LegacyReader(pickle.Unpickler):
    """Allow only historical RDF term constructors and standard value classes."""

    def find_class(self, module, name):
        if module == "rdfcore.term" and name in {
            "URIRef",
            "BNode",
            "Literal",
            "Variable",
            "TripleTerm",
        }:
            from . import term

            return getattr(term, name)
        if module == "datetime" and name in {
            "date",
            "datetime",
            "time",
            "timedelta",
            "timezone",
        }:
            import datetime

            return getattr(datetime, name)
        if module == "decimal" and name == "Decimal":
            from decimal import Decimal

            return Decimal
        raise ValueError("forbidden class in legacy RDF database")


def decode_legacy(data):
    stream = io.BytesIO(data)
    value = LegacyReader(stream).load()
    if stream.read(1):
        raise ValueError("trailing legacy RDF data")
    encode(value, canonical=False)  # Validate the resulting kind and depth.
    return value


def _pack_native(value):
    from datetime import date, datetime, time, timedelta
    from decimal import Decimal
    from ._literal_arithmetic import Duration

    if value is None:
        return ["none"]
    if type(value) is bool:
        return ["bool", value]
    if type(value) is int:
        return ["int", str(value)]
    if type(value) is float:
        return ["float", value.hex()]
    if type(value) is str:
        return ["str", value]
    if type(value) is bytes:
        return ["bytes", value.hex()]
    if isinstance(value, Decimal):
        return ["decimal", str(value)]
    if isinstance(value, datetime):
        return ["datetime", value.isoformat(), value.fold]
    if isinstance(value, time):
        return ["time", value.isoformat(), value.fold]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if isinstance(value, timedelta):
        return ["delta", value.days, value.seconds, value.microseconds]
    if isinstance(value, Duration):
        return [
            "duration",
            str(value.years),
            str(value.months),
            _pack_native(value.tdelta),
        ]
    if type(value) in (dict, list):
        text = json.dumps(value, allow_nan=False, ensure_ascii=True)
        load_json(text.encode())
        return ["json", text]
    # DOM values are reconstructed by their existing datatype lexical mapping.
    if getattr(value, "nodeType", None) is not None:
        return ["lexical"]
    raise TypeError("unsupported native literal value in sort record")


def _unpack_native(state, lexical_value):
    from datetime import date, datetime, time, timedelta
    from decimal import Decimal
    from ._literal_arithmetic import Duration

    if not isinstance(state, list) or not state or not isinstance(state[0], str):
        raise ValueError("invalid native literal state")
    tag, *values = state
    if tag == "lexical" and not values:
        return lexical_value
    if tag == "none" and not values:
        return None
    if tag == "bool" and len(values) == 1 and type(values[0]) is bool:
        return values[0]
    if tag == "delta" and len(values) == 3 and all(type(v) is int for v in values):
        return timedelta(days=values[0], seconds=values[1], microseconds=values[2])
    if (
        tag == "duration"
        and len(values) == 3
        and all(isinstance(v, str) for v in values[:2])
    ):
        delta = _unpack_native(values[2], None)
        if not isinstance(delta, timedelta):
            raise ValueError("invalid duration delta")
        return Duration(Decimal(values[0]), Decimal(values[1]), delta)
    if (
        tag in ("datetime", "time")
        and len(values) == 2
        and isinstance(values[0], str)
        and type(values[1]) is int
        and values[1] in (0, 1)
    ):
        cls = datetime if tag == "datetime" else time
        return cls.fromisoformat(values[0]).replace(fold=values[1])
    if tag == "json" and len(values) == 1 and isinstance(values[0], str):
        value = load_json(values[0].encode())
        if type(value) not in (dict, list):
            raise ValueError("invalid JSON literal state")
        json.dumps(value, allow_nan=False)
        return value
    if len(values) == 1 and isinstance(values[0], str):
        converters = {
            "int": int,
            "float": float.fromhex,
            "str": str,
            "bytes": bytes.fromhex,
            "decimal": Decimal,
            "date": date.fromisoformat,
        }
        if tag in converters:
            return converters[tag](values[0])
    raise ValueError("invalid native literal state")

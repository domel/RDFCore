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
                raise ValueError('stored RDF nesting limit exceeded')
        elif byte in (93, 125):
            depth -= 1
    try:
        return json.loads(raw.decode('utf-8'))
    except (UnicodeError, RecursionError) as error:
        raise ValueError('invalid stored RDF JSON') from error


def encode(term, *, canonical=True):
    from .graph import Graph
    def pack(value, depth=0):
        if depth > MAX_DEPTH:
            raise ValueError('stored RDF nesting limit exceeded')
        if isinstance(value, Graph):
            return ['graph', pack(value.identifier, depth + 1)]
        if value is None:
            return ['none']
        if isinstance(value, Literal):
            language = value.language.lower() if canonical and value.language else value.language
            return ['literal', str(value), language,
                    str(value.datatype) if value.datatype is not None else None, value.direction]
        if isinstance(value, TripleTerm):
            return ['triple', *(pack(item, depth + 1) for item in value)]
        for cls, tag in ((RDFLibGenid, 'rdflib-genid'), (Genid, 'genid'), (URIRef, 'uri'), (BNode, 'blank'), (Variable, 'variable')):
            if isinstance(value, cls):
                return [tag, str(value)]
        raise TypeError('unsupported stored RDF term')
    return json.dumps(pack(term), ensure_ascii=True, separators=(',', ':')).encode('ascii')


def decode_value(value):
    """Validate an already parsed JSON term tree."""
    def unpack(value, depth=0):
        if depth > MAX_DEPTH:
            raise ValueError('stored RDF nesting limit exceeded')
        if not isinstance(value, list) or not value:
            raise ValueError('invalid stored RDF term')
        tag, *parts = value
        if not isinstance(tag, str):
            raise ValueError('invalid stored RDF tag')
        if tag == 'graph' and len(parts) == 1:
            from .graph import Graph
            identifier = unpack(parts[0], depth + 1)
            if not isinstance(identifier, (URIRef, BNode)):
                raise ValueError('invalid stored graph identifier')
            return Graph(identifier=identifier)
        if tag == 'none' and not parts:
            return None
        classes = {'uri': URIRef, 'blank': BNode, 'variable': Variable, 'genid': Genid, 'rdflib-genid': RDFLibGenid}
        if tag in classes and len(parts) == 1 and isinstance(parts[0], str):
            return classes[tag](parts[0])
        if tag == 'literal' and len(parts) == 4:
            lexical, language, datatype, direction = parts
            if not isinstance(lexical, str) or any(x is not None and not isinstance(x, str) for x in parts[1:]):
                raise ValueError('invalid stored literal')
            return Literal(lexical, lang=language, datatype=datatype, direction=direction, normalize=False)
        if tag == 'triple' and len(parts) == 3:
            return TripleTerm(*(unpack(part, depth + 1) for part in parts))
        raise ValueError('invalid stored RDF term')
    try:
        return unpack(value)
    except (TypeError, RecursionError) as error:
        raise ValueError('invalid stored RDF term') from error


def decode(data):
    return decode_value(load_json(data))


class LegacyReader(pickle.Unpickler):
    """Allow only historical RDF term constructors and standard value classes."""

    def find_class(self, module, name):
        if module == 'rdfcore.term' and name in {'URIRef', 'BNode', 'Literal', 'Variable', 'TripleTerm'}:
            from . import term
            return getattr(term, name)
        if module == 'datetime' and name in {'date', 'datetime', 'time', 'timedelta', 'timezone'}:
            import datetime
            return getattr(datetime, name)
        if module == 'decimal' and name == 'Decimal':
            from decimal import Decimal
            return Decimal
        raise ValueError('forbidden class in legacy RDF database')


def decode_legacy(data):
    stream = io.BytesIO(data)
    value = LegacyReader(stream).load()
    if stream.read(1):
        raise ValueError('trailing legacy RDF data')
    encode(value, canonical=False)  # Validate the resulting kind and depth.
    return value

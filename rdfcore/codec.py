"""Version-one storage representation of RDF terms."""

import io
import json
import pickle

from .term import BNode, Literal, TripleTerm, URIRef, Variable


def encode(term):
    def pack(value):
        if value is None:
            return ['none']
        if isinstance(value, Literal):
            return ['literal', str(value), value.language.lower() if value.language else None,
                    str(value.datatype) if value.datatype is not None else None, value.direction]
        if isinstance(value, TripleTerm):
            return ['triple', *(pack(item) for item in value)]
        for cls, tag in ((URIRef, 'uri'), (BNode, 'blank'), (Variable, 'variable')):
            if isinstance(value, cls):
                return [tag, str(value)]
        raise TypeError('unsupported stored RDF term')
    return json.dumps(pack(term), ensure_ascii=True, separators=(',', ':')).encode('ascii')


def decode(data):
    def unpack(value):
        if not isinstance(value, list) or not value:
            raise ValueError('invalid stored RDF term')
        tag, *parts = value
        if tag == 'none' and not parts:
            return None
        classes = {'uri': URIRef, 'blank': BNode, 'variable': Variable}
        if tag in classes and len(parts) == 1 and isinstance(parts[0], str):
            return classes[tag](parts[0])
        if tag == 'literal' and len(parts) == 4:
            lexical, language, datatype, direction = parts
            if not isinstance(lexical, str) or any(x is not None and not isinstance(x, str) for x in parts[1:]):
                raise ValueError('invalid stored literal')
            return Literal(lexical, lang=language, datatype=datatype, direction=direction, normalize=False)
        if tag == 'triple' and len(parts) == 3:
            return TripleTerm(*(unpack(part) for part in parts))
        raise ValueError('invalid stored RDF term')
    return unpack(json.loads(bytes(data)))


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
    return LegacyReader(io.BytesIO(data)).load()

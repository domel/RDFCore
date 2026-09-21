"""Graph API backed by the in-memory store."""

from __future__ import annotations

from pathlib import PurePath

from .exceptions import UniquenessError
from .namespace import OWL, RDF, RDFS, XSD, NamespaceManager
from .store import Memory
from .term import BNode, Literal, TripleTerm, URIRef
from .parser import create_input_source
from .plugin import get as get_plugin
from .parser import Parser
from .serializer import Serializer


class Graph:
    def __init__(self, store="default", identifier=None, namespace_manager=None, base=None, bind_namespaces="rdflib"):
        self.store = store if hasattr(store, "triples") else Memory()
        self.identifier = identifier if identifier is not None else BNode()
        self.base = base
        self.namespace_manager = namespace_manager if namespace_manager is not None else NamespaceManager(self)
        if namespace_manager is None and bind_namespaces == "rdflib":
            for prefix, namespace in (("rdf", RDF), ("rdfs", RDFS), ("xsd", XSD), ("owl", OWL)):
                self.namespace_manager.bind(prefix, namespace)

    def add(self, triple):
        self._assert_triple(triple)
        self.store.add(triple, self.identifier)
        return self

    def addN(self, quads):
        for subject, predicate, obj, context in quads:
            self._assert_triple((subject, predicate, obj))
            context_identifier = getattr(context, "identifier", context)
            if context_identifier == self.identifier:
                self.store.add((subject, predicate, obj), self.identifier)
        return self

    def remove(self, triple):
        self.store.remove(triple, self.identifier)
        return self

    def triples(self, pattern):
        for triple, _ in self.store.triples(pattern, self.identifier):
            yield triple

    def _triples_in_context(self, pattern):
        yield from self.triples(pattern)

    def __iter__(self):
        return self.triples((None, None, None))

    def __len__(self):
        return self.store.__len__(self.identifier)

    def __contains__(self, triple):
        return next(self.triples(triple), None) is not None

    def __getitem__(self, pattern):
        return self.triples(pattern)

    def subjects(self, predicate=None, object=None, unique=False):
        seen = set()
        for subject, _, _ in self.triples((None, predicate, object)):
            if not unique or subject not in seen:
                seen.add(subject)
                yield subject

    def predicates(self, subject=None, object=None, unique=False):
        seen = set()
        for _, predicate, _ in self.triples((subject, None, object)):
            if not unique or predicate not in seen:
                seen.add(predicate)
                yield predicate

    def objects(self, subject=None, predicate=None, unique=False):
        seen = set()
        for _, _, obj in self.triples((subject, predicate, None)):
            if not unique or obj not in seen:
                seen.add(obj)
                yield obj

    def subject_predicates(self, object=None, unique=False):
        seen = set()
        for subject, predicate, _ in self.triples((None, None, object)):
            item = (subject, predicate)
            if not unique or item not in seen:
                seen.add(item)
                yield item

    def subject_objects(self, predicate=None, unique=False):
        seen = set()
        for subject, _, obj in self.triples((None, predicate, None)):
            item = (subject, obj)
            if not unique or item not in seen:
                seen.add(item)
                yield item

    def predicate_objects(self, subject=None, unique=False):
        seen = set()
        for _, predicate, obj in self.triples((subject, None, None)):
            item = (predicate, obj)
            if not unique or item not in seen:
                seen.add(item)
                yield item

    def value(self, subject=None, predicate=None, object=None, default=None, any=True):
        values = []
        for candidate_subject, candidate_predicate, candidate_object in self.triples((subject, predicate, object)):
            if object is None:
                values.append(candidate_object)
            elif subject is None:
                values.append(candidate_subject)
            elif predicate is None:
                values.append(candidate_predicate)
            else:
                values.append(candidate_object)
        if not values:
            return default
        if not any and len(values) > 1:
            raise UniquenessError(f"Found more than one value for {subject!r}, {predicate!r}")
        return values[0]

    def set(self, triple):
        subject, predicate, obj = triple
        self.remove((subject, predicate, None))
        return self.add(triple)

    def bind(self, prefix, namespace, override=True, replace=False):
        self.namespace_manager.bind(prefix, namespace, override, replace)

    def namespaces(self):
        return self.namespace_manager.namespaces()

    def qname(self, uri):
        return self.namespace_manager.qname(uri)

    def compute_qname(self, uri, generate=True):
        return self.namespace_manager.compute_qname(uri, generate)

    def absolutize(self, uri, defrag=1):
        return self.namespace_manager.absolutize(uri)

    def close(self, commit_pending_transaction=False):
        return self.store.close(commit_pending_transaction)

    def parse(self, source=None, publicID=None, format=None, location=None, file=None, data=None, **args):
        if "rdf_version" in args:
            from .rdf_version import validate_rdf_version
            validate_rdf_version(args["rdf_version"])
        if format is None:
            format = _format_from_location(location or source)
        source = create_input_source(source, publicID, location, file, data, format, **args)
        plugin = get_plugin(format, Parser)
        parser_class = plugin.getClass()
        parser = parser_class(self)
        from .streaming import DatasetSink, GraphSink
        sink = DatasetSink(self) if hasattr(self, "quads") else GraphSink(self)
        try:
            parser.parse(source, sink, **args)
        finally:
            source.close()
        return self

    def serialize(self, destination=None, format="turtle", base=None, encoding=None, **args):
        from .rdf_version import required_rdf_version, validate_rdf_version, version_allows

        requested_version = validate_rdf_version(args.get("rdf_version", "auto"))
        downgrade = args.get("downgrade", "error")
        if downgrade not in ("error", "interop"):
            raise ValueError("downgrade must be 'error' or 'interop'")
        required_version = required_rdf_version(self)
        serializable_graph = self
        if required_version != "1.1":
            rdf12_serializer = format in ("nt12", "nq12", "turtle12", "trig12")
            if downgrade == "interop" and requested_version in ("1.1", "1.2-basic"):
                from .interop import interop_downgrade
                serializable_graph = interop_downgrade(self, requested_version)
                required_version = required_rdf_version(serializable_graph)
            if not rdf12_serializer and serializable_graph is self:
                raise ValueError("RDF 1.2 data requires an RDF 1.2 serializer or downgrade='interop'")
            if requested_version == "1.1" and required_version != "1.1":
                raise ValueError(
                    f"{format} serializer cannot represent RDF {required_version} data yet; "
                    "select a compatible RDF 1.2 serializer or an explicit interoperability downgrade"
                )
            if requested_version == "1.2-basic" and required_version == "1.2":
                raise ValueError(f"RDF 1.2 data cannot be serialized as {requested_version}")
        plugin = get_plugin(format, Serializer)
        serializer = plugin.getClass()(serializable_graph)
        if isinstance(destination, (str, PurePath)):
            mode = "wb" if encoding else "w"
            open_kwargs = {} if encoding else {"encoding": "utf-8", "newline": ""}
            with open(destination, mode, **open_kwargs) as stream:
                serializer.serialize(stream, base=base, encoding=encoding, **args)
            return self
        result = serializer.serialize(destination, base=base, encoding=encoding, **args)
        return self if destination is not None else result

    def __add__(self, other):
        result = Graph()
        for triple in self:
            result.add(triple)
        for triple in other:
            result.add(triple)
        return result

    def __sub__(self, other):
        result = Graph()
        for triple in self:
            if triple not in other:
                result.add(triple)
        return result

    def __and__(self, other):
        result = Graph()
        for triple in self:
            if triple in other:
                result.add(triple)
        return result

    __mul__ = __and__

    def __iadd__(self, other):
        for triple in other:
            self.add(triple)
        return self

    def __isub__(self, other):
        for triple in other:
            self.remove(triple)
        return self

    @staticmethod
    def _assert_triple(triple):
        if not isinstance(triple, tuple) or len(triple) != 3:
            raise TypeError("triple must be a 3-tuple")
        subject, predicate, obj = triple
        if not isinstance(subject, (URIRef, BNode)):
            raise TypeError("subject must be a URIRef or BNode")
        if not isinstance(predicate, URIRef):
            raise TypeError("predicate must be a URIRef")
        if not isinstance(obj, (URIRef, BNode, Literal, TripleTerm)):
            raise TypeError("object must be a URIRef, BNode, or Literal")


def _format_from_location(location):
    if location is not None:
        name = str(location).lower().split("?", 1)[0]
        suffix = name.rsplit(".", 1)[-1] if "." in name else ""
        return {"ttl": "turtle", "turtle": "turtle", "nt": "nt", "ntriples": "ntriples", "nquads": "nquads", "trig": "trig"}.get(suffix, "turtle")
    return "turtle"

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

    def items(self, list):
        """Yield the members of an RDF collection."""
        current = list
        seen = set()
        while current and current != RDF.nil:
            if current in seen:
                raise ValueError("List contains a recursive rdf:rest reference")
            seen.add(current)
            item = self.value(current, RDF.first)
            if item is not None:
                yield item
            current = self.value(current, RDF.rest)

    def transitiveClosure(self, func, arg, seen=None):
        """Yield the depth-first transitive closure of a user function."""
        if seen is None:
            seen = {}
        elif arg in seen:
            return
        seen[arg] = 1
        for result in func(arg, self):
            yield result
            yield from self.transitiveClosure(func, result, seen)

    def transitive_objects(self, subject, predicate, remember=None):
        """Yield ``subject`` and all objects reachable through ``predicate``."""
        if remember is None:
            remember = {}
        if subject in remember:
            return
        remember[subject] = 1
        yield subject
        for obj in self.objects(subject, predicate):
            yield from self.transitive_objects(obj, predicate, remember)

    def transitive_subjects(self, predicate, object, remember=None):
        """Yield ``object`` and all subjects reaching it through ``predicate``."""
        if remember is None:
            remember = {}
        if object in remember:
            return
        remember[object] = 1
        yield object
        for subject in self.subjects(predicate, object):
            yield from self.transitive_subjects(predicate, subject, remember)

    def all_nodes(self):
        nodes = set(self.objects())
        nodes.update(self.subjects())
        return nodes

    def connected(self):
        """Return whether all graph nodes belong to one undirected component."""
        nodes = self.all_nodes()
        if not nodes:
            return False
        start = next(iter(nodes))
        visited = set()
        pending = [start]
        while pending:
            node = pending.pop()
            if node in visited:
                continue
            visited.add(node)
            pending.extend(self.objects(subject=node))
            pending.extend(self.subjects(object=node))
        return visited == nodes

    def isomorphic(self, other):
        """Compare this graph with another graph up to blank-node names."""
        from .compare import isomorphic

        return isomorphic(self, other)

    def triples_choices(self, triple, context=None):
        """Yield triples matching scalar or list choices in a pattern."""
        subject, predicate, object = triple
        choices = [
            value if isinstance(value, (list, tuple, set, frozenset)) else (value,)
            for value in (subject, predicate, object)
        ]
        seen = set()
        for chosen_subject in choices[0]:
            for chosen_predicate in choices[1]:
                for chosen_object in choices[2]:
                    for result in self.triples((chosen_subject, chosen_predicate, chosen_object)):
                        if result not in seen:
                            seen.add(result)
                            yield result

    @staticmethod
    def _map_skolem_term(term, *, to_skolem, authority=None, basepath=None):
        if isinstance(term, BNode) and to_skolem:
            return term.skolemize(authority=authority, basepath=basepath)
        if isinstance(term, URIRef) and not to_skolem:
            try:
                return term.de_skolemize()
            except Exception:
                return term
        if isinstance(term, TripleTerm):
            return TripleTerm(
                Graph._map_skolem_term(term.subject, to_skolem=to_skolem, authority=authority, basepath=basepath),
                Graph._map_skolem_term(term.predicate, to_skolem=to_skolem, authority=authority, basepath=basepath),
                Graph._map_skolem_term(term.object, to_skolem=to_skolem, authority=authority, basepath=basepath),
            )
        return term

    def skolemize(self, new_graph=None, bnode=None, authority=None, basepath=None):
        result = Graph() if new_graph is None else new_graph
        for subject, predicate, obj in self:
            if bnode is None:
                mapper = lambda value: self._map_skolem_term(
                    value, to_skolem=True, authority=authority, basepath=basepath
                )
            else:
                mapper = lambda value: self._map_selected_skolem_term(
                    value, bnode, to_skolem=True, authority=authority, basepath=basepath
                )
            result.add((mapper(subject), mapper(predicate), mapper(obj)))
        return result

    def de_skolemize(self, new_graph=None, uriref=None):
        result = Graph() if new_graph is None else new_graph
        for subject, predicate, obj in self:
            def mapper(value):
                if uriref is None:
                    return self._map_skolem_term(value, to_skolem=False)
                return self._map_selected_skolem_term(value, uriref, to_skolem=False)
            result.add((mapper(subject), mapper(predicate), mapper(obj)))
        return result

    @staticmethod
    def _map_selected_skolem_term(term, selected, *, to_skolem, authority=None, basepath=None):
        if term == selected:
            return (
                term.skolemize(authority=authority, basepath=basepath)
                if to_skolem else term.de_skolemize()
            )
        if isinstance(term, TripleTerm):
            return TripleTerm(
                Graph._map_selected_skolem_term(term.subject, selected, to_skolem=to_skolem, authority=authority, basepath=basepath),
                Graph._map_selected_skolem_term(term.predicate, selected, to_skolem=to_skolem, authority=authority, basepath=basepath),
                Graph._map_selected_skolem_term(term.object, selected, to_skolem=to_skolem, authority=authority, basepath=basepath),
            )
        return term

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

    def n3(self, namespace_manager=None):
        """Return the graph identifier in RDFLib-compatible N3 form."""
        return "[" + self.identifier.n3(namespace_manager=namespace_manager) + "]"

    def collection(self, identifier):
        from .collection import Collection
        return Collection(self, identifier)

    def resource(self, identifier):
        from .resource import Resource
        if not isinstance(identifier, (URIRef, BNode)):
            identifier = URIRef(identifier)
        return Resource(self, identifier)

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

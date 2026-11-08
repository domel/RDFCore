"""Graph API backed by the in-memory store."""

from __future__ import annotations

from pathlib import PurePath

from .exceptions import UniquenessError
from .namespace import OWL, RDF, RDFS, XSD, NamespaceManager
from .store import Memory, SQLiteStore
from .term import BNode, Genid, RDFLibGenid, Literal, Node, TripleTerm, URIRef
from .parser import create_input_source
from .plugin import get as get_plugin
from .parser import Parser
from .serializer import Serializer


class Graph(Node):
    def __init__(self, store="default", identifier=None, namespace_manager=None, base=None, bind_namespaces="rdflib"):
        from .store import Store
        if not isinstance(store, Store):
            store = get_plugin(store, Store).getClass()()
        self.store = store
        if identifier and not isinstance(identifier, (URIRef, BNode)):
            ' ' in identifier
        self.identifier = BNode() if not identifier else identifier if isinstance(identifier, (URIRef, BNode)) else URIRef(identifier)
        self.base = base
        self._namespace_manager = namespace_manager
        self._bind_namespaces = bind_namespaces

    @property
    def namespace_manager(self):
        if self._namespace_manager is None:
            self._namespace_manager = NamespaceManager(self, bind_namespaces=self._bind_namespaces)
        return self._namespace_manager

    @namespace_manager.setter
    def namespace_manager(self, manager):
        self._namespace_manager = manager

    def add(self, triple, *, validate=False):
        subject, predicate, obj = triple
        triple = subject, predicate, obj
        if validate or any(isinstance(item, TripleTerm) or isinstance(item, Literal) and item.direction is not None for item in triple):
            self._assert_triple(triple)
        else:
            subject, predicate, obj = triple
            for label, item in zip(('Subject', 'Predicate', 'Object'), (subject, predicate, obj)):
                assert isinstance(item, Node), '%s %s must be an rdflib term' % (label, item)
        self.store.add(triple, self._store_graph_context())
        if hasattr(self.store, '_conjunctive_views'):
            self.store._conjunctive_views[self.identifier] = self
            self.store._conjunctive_contexts.setdefault(self.identifier, self)
        return self

    def addN(self, quads):
        def selected():
            for subject, predicate, obj, context in quads:
                if isinstance(context, Graph) and context.identifier is self.identifier:
                    if any(isinstance(item, TripleTerm) or isinstance(item, Literal) and item.direction is not None
                           for item in (subject, predicate, obj)):
                        self._assert_triple((subject, predicate, obj))
                    else:
                        for item in (subject, predicate, obj):
                            assert isinstance(item, Node), 'Term %s must be an rdflib term' % (item,)
                    yield subject, predicate, obj, context
        self.store.addN(selected())
        return self

    def _store_graph_context(self):
        return self.identifier if isinstance(self.store, (Memory, SQLiteStore)) else self

    def remove(self, triple):
        self.store.remove(triple, self._store_graph_context())
        return self

    def triples(self, triple):
        for triple, _ in self.store.triples(triple, self._store_graph_context()):
            yield triple

    def _triples_in_context(self, pattern):
        yield from self.triples(pattern)

    def __iter__(self):
        return self.triples((None, None, None))

    def __len__(self):
        return self.store.__len__(self._store_graph_context())

    def __eq__(self, other):
        return isinstance(other, Graph) and self.identifier == other.identifier

    def __hash__(self):
        return hash(self.identifier)

    def __contains__(self, triple):
        return next(self.triples(triple), None) is not None

    def __getitem__(self, item):
        if isinstance(item, slice):
            subject, predicate, obj = item.start, item.stop, item.step
            if subject is None and predicate is None and obj is None:
                return self.triples((None, None, None))
            if subject is None and predicate is None:
                return self.subject_predicates(obj)
            if subject is None and obj is None:
                return self.subject_objects(predicate)
            if predicate is None and obj is None:
                return self.predicate_objects(subject)
            if subject is None:
                return self.subjects(predicate, obj)
            if predicate is None:
                return self.predicates(subject, obj)
            if obj is None:
                return self.objects(subject, predicate)
            return (subject, predicate, obj) in self
        if isinstance(item, Node):
            return self.predicate_objects(item)
        raise TypeError('You can only index a graph by a single RDF term or a slice of RDF terms.')

    def subjects(self, predicate=None, object=None, unique=False):
        if isinstance(object, list):
            for selected in object:
                yield from self.subjects(predicate, selected, unique)
            return
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
        if isinstance(subject, list):
            for selected in subject:
                yield from self.objects(selected, predicate, unique)
            return
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
        """RDFLib's approximate check; RDF 1.2 terms use exact comparison.

        Use ``rdfcore.compare.isomorphic`` for exact RDF 1.1 comparison too.
        """
        if len(self) != len(other):
            return False
        from .rdf_version import required_rdf_version
        if required_rdf_version(self) != '1.1' or required_rdf_version(other) != '1.1':
            from .compare import isomorphic
            return isomorphic(self, other)
        for source, target in ((self, other), (other, self)):
            for s, p, o in source:
                if not isinstance(s, BNode) and not isinstance(o, BNode) and (s, p, o) not in target:
                    return False
        return True

    def triples_choices(self, triple, context=None):
        """RDFLib list choices, retaining duplicate results and empty wildcards."""
        for row, _ in self.store.triples_choices(triple, context=self._store_graph_context()):
            yield row

    @staticmethod
    def _choices(triple, triples):
        subject, predicate, obj = triple
        if isinstance(obj, list):
            assert not isinstance(subject, list), 'object_ / subject are both lists'
            assert not isinstance(predicate, list), 'object_ / predicate are both lists'
            slot, choices = 2, obj
        elif isinstance(subject, list):
            assert not isinstance(predicate, list), 'subject / predicate are both lists'
            slot, choices = 0, subject
        elif isinstance(predicate, list):
            slot, choices = 1, predicate
        else:
            return
        for choice in choices or [None]:
            pattern = list(triple)
            pattern[slot] = choice
            yield from triples(tuple(pattern))

    @staticmethod
    def _map_skolem_term(term, *, to_skolem, authority=None, basepath=None):
        if isinstance(term, BNode) and to_skolem:
            return term.skolemize(authority=authority, basepath=basepath)
        if isinstance(term, URIRef) and not to_skolem:
            try:
                return (RDFLibGenid(term) if RDFLibGenid._is_rdflib_skolem(term) else Genid(term) if Genid._is_external_skolem(term) else term).de_skolemize()
            except Exception:
                return term
        if isinstance(term, TripleTerm):
            return TripleTerm(
                Graph._map_skolem_term(term.subject, to_skolem=to_skolem, authority=authority, basepath=basepath),
                term.predicate,
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
            result.add((mapper(subject), predicate, mapper(obj)))
        return result

    def de_skolemize(self, new_graph=None, uriref=None):
        result = Graph() if new_graph is None else new_graph
        if uriref is not None and not isinstance(uriref, Genid):
            from .rdf_version import required_rdf_version
            if required_rdf_version(self) == '1.1':
                return result
        for subject, predicate, obj in self:
            def mapper(value):
                if uriref is None:
                    return self._map_skolem_term(value, to_skolem=False)
                return self._map_selected_skolem_term(value, uriref, to_skolem=False)
            result.add((mapper(subject), predicate, mapper(obj)))
        return result

    @staticmethod
    def _map_selected_skolem_term(term, selected, *, to_skolem, authority=None, basepath=None):
        if term == selected:
            return (
                term.skolemize(authority=authority, basepath=basepath)
                if to_skolem else Graph._map_skolem_term(term, to_skolem=False)
            )
        if isinstance(term, TripleTerm):
            return TripleTerm(
                Graph._map_selected_skolem_term(term.subject, selected, to_skolem=to_skolem, authority=authority, basepath=basepath),
                term.predicate,
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

    def value(self, subject=None, predicate=RDF.value, object=None, default=None, any=True):
        if (subject is None and predicate is None) or (subject is None and object is None) or (predicate is None and object is None):
            return None
        if object is None:
            values = self.objects(subject, predicate)
        elif subject is None:
            values = self.subjects(predicate, object)
        elif predicate is None:
            values = self.predicates(subject, object)
        else:
            raise UnboundLocalError("cannot access local variable 'values' where it is not associated with a value")
        try:
            value = next(values)
        except StopIteration:
            return default
        if any is False:
            try:
                next(values)
                message = (
                    'While trying to find a value for (%s, %s, %s) the'
                    ' following multiple values where found:\n'
                    % (subject, predicate, object)
                )
                for (s, p, o), contexts in self.store.triples((subject, predicate, object), None):
                    # Only the exact built-in stores require this fallback.
                    # Custom stores (including subclasses) own the contexts
                    # returned by triples(); an empty iterable is valid.
                    contexts = list(contexts)
                    if not contexts and type(self.store) in (Memory, SQLiteStore):
                        contexts = list(self.store.contexts((s, p, o)))
                    message += '(%s, %s, %s)\n (contexts: %s)\n' % (s, p, o, contexts)
                raise UniquenessError(message)
            except StopIteration:
                pass
        return value

    def set(self, triple):
        subject, predicate, obj = triple
        assert subject is not None, "s can't be None in .set([s,p,o]), as it would remove (*, p, *)"
        assert predicate is not None, "p can't be None in .set([s,p,o]), as it would remove (s, *, *)"
        self.remove((subject, predicate, None))
        return self.add(triple)

    def bind(self, prefix, namespace, override=True, replace=False):
        self.namespace_manager.bind(prefix, namespace, override, replace)

    def namespaces(self):
        yield from self.namespace_manager.namespaces()

    def qname(self, uri):
        return self.namespace_manager.qname(uri)

    def compute_qname(self, uri, generate=True):
        return self.namespace_manager.compute_qname(uri, generate)

    def absolutize(self, uri, defrag=1):
        return self.namespace_manager.absolutize(uri, defrag)

    def n3(self, namespace_manager=None):
        """Return the graph identifier in RDFLib-compatible N3 form."""
        return "[" + self.identifier.n3(namespace_manager=namespace_manager) + "]"

    def collection(self, identifier):
        from .collection import Collection
        return Collection(self, identifier)

    def resource(self, identifier):
        from .resource import Resource
        if not isinstance(identifier, Node):
            identifier = URIRef(identifier)
        return Resource(self, identifier)

    def close(self, commit_pending_transaction=False):
        return self.store.close(commit_pending_transaction)

    def open(self, configuration, create=False):
        return self.store.open(configuration, create)

    def commit(self):
        self.store.commit()
        return self

    def rollback(self):
        self.store.rollback()
        return self

    def destroy(self, configuration):
        self.store.destroy(configuration)
        return self

    def parse(self, source=None, publicID=None, format=None, location=None, file=None, data=None, **args):
        automatic_format = format is None
        if "rdf_version" in args:
            from .rdf_version import validate_rdf_version
            validate_rdf_version(args["rdf_version"])
        if format is None:
            candidate = location if location is not None else file if file is not None else source
            if source is not None and hasattr(source, "read"):
                candidate = None
            format = _format_from_location(candidate)
        source = create_input_source(source, publicID, location, file, data,
                                     None if automatic_format else format, **args)
        parser_class = None
        try:
            if automatic_format and source.content_type:
                # Content-Type takes precedence over a URL suffix. Explicit
                # caller formats still win, including over malformed headers.
                from .exceptions import PluginException
                media = source.content_type.split(';', 1)[0].strip().lower()
                try:
                    get_plugin(source.content_type, Parser)
                except PluginException:
                    # Unknown media parameters do not invalidate a registered
                    # base type. Exact registry entries and known versioned
                    # profiles above have priority over this fallback.
                    try:
                        get_plugin(media, Parser)
                    except PluginException:
                        pass
                    else:
                        format = media
                else:
                    format = source.content_type
            plugin = get_plugin(format, Parser)
            parser_class = plugin.getClass()
            parser = parser_class(self)
            from .streaming import DatasetSink, GraphSink
            sink = DatasetSink(self) if hasattr(self, "quads") else GraphSink(self)
            parser.parse(source, sink, **args)
        finally:
            self._close_parser_source(source, parser_class)
        return self

    def _close_parser_source(self, source, parser_class):
        source.close()

    def serialize(self, destination=None, format="turtle", base=None, encoding=None, **args):
        from .rdf_version import required_rdf_version, validate_rdf_version, version_allows
        from .plugin import resolve_format
        from .media import version_options

        format, media_version = resolve_format(format, Serializer)
        selected_plugin = get_plugin(format, Serializer)
        builtin = selected_plugin.getClass().__module__.startswith('rdfcore.plugins.serializers.')
        args = version_options(args, media_version)

        if base is None:
            base = self.base
        requested_version = validate_rdf_version(args.get("rdf_version", "auto"))
        downgrade = args.get("downgrade", "error")
        if downgrade not in ("error", "interop"):
            raise ValueError("downgrade must be 'error' or 'interop'")
        graph_formats = {'nt', 'nt11', 'ntriples', 'application/n-triples', 'nt12',
                         'turtle', 'ttl', 'turtle11', 'text/turtle', 'turtle12',
                         'xml', 'rdfxml', 'application/rdf+xml', 'xml12', 'xmlrdf12'}
        projection = builtin and hasattr(self, 'quads') and format in graph_formats
        policy = args.pop('dataset_policy', None) if projection else None
        if policy is not None and policy not in ('strict', 'default', 'union'):
            raise ValueError("dataset_policy must be 'strict', 'default', or 'union'")
        if projection and policy is None and (format in {'nt12', 'turtle12', 'xml12', 'xmlrdf12'}
                                              or downgrade == 'interop'):
            policy = 'strict'
        if projection and policy == 'strict' and any(
                context != self.default_graph.identifier for context in self.store.contexts()):
            raise ValueError('named graph requires an explicit dataset_policy for graph output')
        # Preserve RDFLib's legacy default projection. Explicit extension
        # policies use read-only views, independent of default_union.
        required_source = _DatasetProjection(self, policy) if projection and policy is not None else self
        required_version = required_rdf_version(required_source)
        serializable_graph = required_source
        if required_version != "1.1":
            rdf12_serializer = format in ("nt12", "nq12", "turtle12", "trig12", "xml12", "xmlrdf12")
            if downgrade == "interop" and requested_version in ("1.1", "1.2-basic"):
                from .interop import interop_downgrade
                serializable_graph = interop_downgrade(required_source, requested_version)
                required_version = required_rdf_version(serializable_graph)
            if builtin and not rdf12_serializer and downgrade != 'interop':
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
            binary = bool(encoding) or getattr(serializer, '_binary_output', False)
            mode = "wb" if binary else "w"
            open_kwargs = {} if binary else {"encoding": "utf-8", "newline": ""}
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
        self.addN((subject, predicate, obj, self) for subject, predicate, obj in other)
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


class _DatasetProjection(Graph):
    """Read-only serialization view; no graph/context registration or copy."""

    def __init__(self, source, policy):
        super().__init__(store=source.store, identifier=source.default_graph.identifier,
                         namespace_manager=source.namespace_manager, base=source.base)
        self._context = None if policy == 'union' else source.default_graph.identifier

    def triples(self, pattern):
        for triple, _ in self.store.triples(pattern, self._context):
            yield triple


def _format_from_location(location):
    if location is not None:
        location = getattr(location, "name", location)
        name = str(location).lower().split("?", 1)[0]
        suffix = name.rsplit(".", 1)[-1] if "." in name else ""
        return {"ttl": "turtle", "turtle": "turtle", "nt": "nt", "ntriples": "ntriples", "nq": "nquads", "nquads": "nquads", "trig": "trig", "rdf": "xml", "xml": "xml"}.get(suffix, "turtle")
    return "turtle"

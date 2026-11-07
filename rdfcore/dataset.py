"""RDF dataset and legacy conjunctive graph APIs."""

from __future__ import annotations

import warnings
import typing as _typing

from .graph import Graph
from .term import BNode, URIRef

DATASET_DEFAULT_GRAPH_ID = URIRef("urn:x-rdflib:default")


class ConjunctiveGraph(Graph):
    # Dataset conveniences retained as RDFCore extensions; the class itself
    # follows RDFLib's Graph hierarchy and union-query contract.

    if _typing.TYPE_CHECKING:
        # These extension methods are attached below after Dataset is defined.
        def graph(self, identifier=None, base=None) -> Graph: ...
        def graphs(self, triple=None) -> _typing.Iterator[Graph]: ...
        def context_id(self, uri, context_id=None) -> URIRef: ...
        def remove_context(self, context) -> None: ...
        def remove_graph(self, g) -> ConjunctiveGraph: ...
        def add_graph(self, g) -> Graph: ...

    def contexts(self, triple=None):
        for context in self.store.contexts(triple):
            if isinstance(context, Graph):
                yield context
            else:
                yield self._context_view(context)

    def _context_view(self, identifier, latest=False):
        name = '_conjunctive_views' if latest else '_conjunctive_contexts'
        cache = getattr(self.store, name, {})
        return cache[identifier] if identifier in cache else self.get_context(identifier)

    def get_graph(self, identifier):
        return [graph for graph in self.contexts() if graph.identifier == identifier][0]

    def get_context(self, identifier, quoted=False, base=None):
        self._validate_identifier(identifier)
        return Graph(store=self.store, identifier=identifier or None,
                     namespace_manager=self.namespace_manager, base=base)

    @staticmethod
    def _validate_identifier(identifier):
        if identifier and not isinstance(identifier, (URIRef, BNode)):
            # RDFLib URIRef checks membership before converting to text.
            ' ' in identifier

    def _graph(self, context):
        if context is None or isinstance(context, (ConjunctiveGraph, Dataset)):
            return context
        return self.get_context(context.identifier if isinstance(context, Graph) else context)

    def _spoc(self, triple_or_quad, default=False):
        if triple_or_quad is None:
            return None, None, None, self.default_context if default else None
        if len(triple_or_quad) == 3:
            subject, predicate, obj = triple_or_quad
            context = self.default_context if default else None
        elif len(triple_or_quad) == 4:
            subject, predicate, obj, context = triple_or_quad
            context = self._graph(context)
        return subject, predicate, obj, context

    def triples(self, triple_or_quad, context=None):
        subject, predicate, obj, selected = self._spoc(triple_or_quad)
        selected = self._graph(context or selected)
        if self.default_union:
            if selected == self.default_context:
                selected = None
        elif selected is None:
            selected = self.default_context
        identifier = self._store_context(selected)
        for triple, _ in self.store.triples((subject, predicate, obj), identifier):
            yield triple

    def quads(self, triple_or_quad=None):
        subject, predicate, obj, context = self._spoc(triple_or_quad)
        identifier = self._store_context(context)
        from .store import Memory, SQLiteStore
        for triple, contexts in self.store.triples((subject, predicate, obj), identifier):
            if (isinstance(self.store, (Memory, SQLiteStore)) and isinstance(contexts, tuple)
                    and not any(isinstance(item, Graph) for item in contexts)):
                contexts = (self._context_view(key, latest=True)
                            for key in self.store.contexts(triple))
            for selected in contexts:
                yield (*triple, selected)

    def __contains__(self, triple_or_quad):
        subject, predicate, obj, context = self._spoc(triple_or_quad)
        return next(self.triples((subject, predicate, obj), context=context), None) is not None

    def __len__(self):
        return self.store.__len__()

    def triples_choices(self, triple, context=None):
        yield from Dataset.triples_choices(self, triple, context)

    def _store_context(self, context):
        from .store import Memory, SQLiteStore
        return getattr(context, 'identifier', context) if isinstance(self.store, (Memory, SQLiteStore)) else context

    def _assert_nodes(self, subject, predicate, obj):
        from .term import Node, TripleTerm
        from .term import Literal
        if any(isinstance(term, TripleTerm) or isinstance(term, Literal) and term.direction is not None
               for term in (subject, predicate, obj)):
            self._assert_triple((subject, predicate, obj))
        else:
            for term in (subject, predicate, obj):
                assert isinstance(term, Node), 'Term %s must be an rdflib term' % (term,)

    def add(self, triple_or_quad):
        subject, predicate, obj, context = self._spoc(triple_or_quad, default=True)
        self._assert_nodes(subject, predicate, obj)
        self.store.add((subject, predicate, obj), self._store_context(context), quoted=False)
        if context is not None and hasattr(self.store, '_conjunctive_views'):
            self.store._conjunctive_views[context.identifier] = context
            self.store._conjunctive_contexts.setdefault(context.identifier, context)
        return self

    def addN(self, quads):
        def checked():
            for subject, predicate, obj, context in quads:
                self._assert_nodes(subject, predicate, obj)
                context = self._graph(context)
                yield subject, predicate, obj, context
        self.store.addN(checked())
        return self

    def remove(self, triple_or_quad):
        subject, predicate, obj, context = self._spoc(triple_or_quad)
        self.store.remove((subject, predicate, obj), self._store_context(context))
        return self

    def _close_parser_source(self, source, parser_class):
        from .plugins.parsers.rdfxml import RDFXMLParser
        if parser_class is RDFXMLParser:
            # RDFLib's SAX RDF/XML reader closes caller-provided streams,
            # unlike its Turtle reader. Keep this legacy class's contract.
            for stream in (source.getCharacterStream(), source.getByteStream()):
                if stream is not None:
                    stream.close()
        source.close()

    def parse(self, source=None, publicID=None, format=None, location=None, file=None, data=None, **args):
        from pathlib import Path, PurePath
        from urllib.parse import urljoin, urlsplit
        system_id = None
        if file is not None:
            # RDFLib FileInputSource requires this even for in-memory files.
            system_id = Path(file.name).absolute().as_uri()
        candidate = location if location is not None else source
        remote = isinstance(candidate, str) and urlsplit(candidate).scheme in ('http', 'https')
        if not remote:
            if isinstance(candidate, (str, PurePath)):
                system_id = str(candidate) if urlsplit(str(candidate)).scheme == 'file' else Path(candidate).absolute().as_uri()
            elif source is not None and isinstance(getattr(source, 'name', None), (str, PurePath)):
                system_id = Path(source.name).absolute().as_uri()
            if not publicID:
                publicID = system_id or Path.cwd().as_uri() + '/'
        if publicID:
            publicID = urljoin(Path.cwd().as_uri() + '/', publicID)
        if getattr(self.default_context.parse, '__func__', None) is not Graph.parse:
            from .parser import create_input_source
            input_source = create_input_source(source=source, publicID=publicID, format=format,
                                               location=location, file=file, data=data, **args)
            self.default_context.parse(input_source, publicID=publicID, format=format, **args)
            return self
        target = self
        if self.default_context.store is not self.store:
            target = _ConjunctiveParseView(store=self.default_context.store,
                                            identifier=self.default_context.identifier)
            target.default_context = self.default_context
            target.namespace_manager = self.default_context.namespace_manager
        Graph.parse(target, source=source, publicID=publicID, format=format,
                    location=location, file=file, data=data, **args)
        return self

    def __iter__(self):
        return self.triples((None, None, None))

    def __init__(self, store="default", identifier=None, default_graph_base=None):
        self._validate_identifier(identifier)
        from .store import Store
        if not isinstance(store, Store):
            from .plugin import get
            store = get(store, Store).getClass()()
        Graph.__init__(self, store=store, identifier=identifier or None)
        if type(self) is ConjunctiveGraph:
            warnings.warn("ConjunctiveGraph is deprecated, use Dataset instead.",
                          DeprecationWarning, stacklevel=2)
        assert self.store.context_aware, "ConjunctiveGraph must be backed by a context aware store."
        self.context_aware = True
        self.default_union = True
        from .store import Memory, SQLiteStore
        if isinstance(self.store, (Memory, SQLiteStore)) and not hasattr(self.store, '_conjunctive_views'):
            self.store._conjunctive_views = {}
            self.store._conjunctive_contexts = {
                key: self.get_context(key) for key in self.store.contexts()
            }
        self.default_graph = Graph(store=self.store, identifier=identifier or BNode(),
                                   base=default_graph_base)
        self._graphs = {self.default_graph.identifier: self.default_graph}

    @property
    def default_context(self):
        return self.default_graph

    @default_context.setter
    def default_context(self, value):
        self.default_graph = value




class Dataset(ConjunctiveGraph):
    def __init__(self, store="default", default_union=False, default_graph_base=None):
        Graph.__init__(self, store=store)
        assert self.store.context_aware, 'ConjunctiveGraph must be backed by a context aware store.'
        if not self.store.graph_aware:
            raise Exception('Dataset must be backed by a graph-aware store!')
        self.context_aware = True
        self.default_union = default_union
        self.default_graph = Graph(store=self.store, identifier=DATASET_DEFAULT_GRAPH_ID,
                                   base=default_graph_base)
        self._graphs = {}

    def graph(self, identifier=None, base=None):
        if identifier is None:
            self.bind('genid', 'https://rdflib.github.io/.well-known/genid/rdflib/', override=False)
            identifier = BNode().skolemize()
        source = identifier if isinstance(identifier, Graph) and not isinstance(identifier, (Dataset, ConjunctiveGraph)) else None
        graph = self._graph(identifier)
        if source is not None:
            graph += source
        graph.base = base
        self.store.add_graph(graph)
        self._graphs.setdefault(graph.identifier, graph)
        return graph

    def get_graph(self, identifier):
        return ConjunctiveGraph.get_graph(self, identifier)

    def get_context(self, identifier, quoted=False, base=None):
        """Return the graph view for an identifier, creating the view if needed."""
        if isinstance(identifier, str) and not isinstance(identifier, (URIRef, BNode)):
            identifier = URIRef(identifier)
        return Graph(store=self.store, identifier=identifier,
                     namespace_manager=self.namespace_manager, base=base)

    def add_graph(self, g):
        """Compatibility alias for :meth:`graph`."""
        return self.graph(g)

    def context_id(self, uri, context_id=None):
        """Return a context URI using RDFLib's ``URI#context`` convention."""
        uri = uri.split("#", 1)[0]
        if context_id is None:
            context_id = "#context"
        return URIRef(context_id, base=uri)

    def add(self, triple_or_quad):
        subject, predicate, obj, graph = ConjunctiveGraph._spoc(self, triple_or_quad, default=True)
        ConjunctiveGraph._assert_nodes(self, subject, predicate, obj)
        self.store.add((subject, predicate, obj), ConjunctiveGraph._store_context(self, graph))
        if graph is not None and hasattr(self.store, '_conjunctive_views'):
            self.store._conjunctive_views[graph.identifier] = graph
            self.store._conjunctive_contexts.setdefault(graph.identifier, graph)
        return self

    def _graph(self, context):
        return ConjunctiveGraph._graph(self, context)

    def addN(self, quads):
        return ConjunctiveGraph.addN(self, quads)

    def triples(self, triple_or_quad, context=None):
        yield from ConjunctiveGraph.triples(self, triple_or_quad, context)

    def __len__(self):
        return self.store.__len__(None)

    def triples_choices(self, triple, context=None):
        selected = self.default_graph if context is None and not self.default_union else self._graph(context)
        for row, _ in self.store.triples_choices(triple, context=self._store_context(selected)):
            yield row

    def __iter__(self):
        return self.quads()

    def _triples_in_context(self, pattern):
        for triple, _ in self.store.triples(pattern, self.default_graph.identifier):
            yield triple

    def serialize(self, destination=None, format="trig", base=None, encoding=None, **args):
        return super().serialize(destination=destination, format=format, base=base, encoding=encoding, **args)

    def parse(self, source=None, publicID=None, format=None, location=None, file=None, data=None, **args):
        from .streaming import BoundedReadStream
        if isinstance(file, BoundedReadStream) and not hasattr(file, 'name') and source is None and location is None and data is None:
            source, file = file, None
        return super().parse(source=source, publicID=publicID, format=format,
                             location=location, file=file, data=data, **args)

    def quads(self, quad=None):
        for subject, predicate, obj, graph in ConjunctiveGraph.quads(self, quad):
            yield subject, predicate, obj, graph.identifier

    def graphs(self, triple=None):
        seen = set()
        for graph in ConjunctiveGraph.contexts(self, triple):
            seen.add(graph.identifier)
            yield graph
        default_id = DATASET_DEFAULT_GRAPH_ID if isinstance(self, Dataset) else self.default_graph.identifier
        if default_id not in seen:
            yield self.graph(default_id)

    def remove(self, triple_or_quad):
        subject, predicate, obj, graph = ConjunctiveGraph._spoc(self, triple_or_quad)
        self.store.remove((subject, predicate, obj), ConjunctiveGraph._store_context(self, graph))
        return self

    def remove_graph(self, g):
        identifier = getattr(g, "identifier", g)
        if identifier == self.default_graph.identifier:
            self.default_graph.remove((None, None, None))
        else:
            self.store.remove_context(identifier)
            self._graphs.pop(identifier, None)
        return self

    def remove_context(self, context) -> None:
        """Remove a context's triples, retaining the graph, as in RDFLib.

        ``None`` selects the union. Context identifiers retain their term
        types: a plain string is not an IRI. The return value is ``None``.
        """
        self.store.remove((None, None, None), context)

    @property
    def default_context(self):
        warnings.warn("default_context is deprecated; use default_graph", DeprecationWarning, stacklevel=2)
        return self.default_graph

    @default_context.setter
    def default_context(self, value):
        warnings.warn("Dataset.default_context is deprecated, use Dataset.default_graph instead.",
                      DeprecationWarning, stacklevel=2)
        self.default_graph = value

    def contexts(self, triple=None):
        warnings.warn("contexts is deprecated; use graphs", DeprecationWarning, stacklevel=2)
        yield from self.graphs(triple)




for _method in ('graph', 'graphs', 'context_id', 'remove_context', 'remove_graph',
                'add_graph', '_triples_in_context'):
    setattr(ConjunctiveGraph, _method, getattr(Dataset, _method))

class _ConjunctiveParseView(ConjunctiveGraph):
    """Internal parser target when the default context uses another store."""

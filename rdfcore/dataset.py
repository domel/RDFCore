"""RDF dataset and legacy conjunctive graph APIs."""

from __future__ import annotations

import warnings

from .graph import Graph
from .term import BNode, URIRef

DATASET_DEFAULT_GRAPH_ID = URIRef("urn:x-rdflib:default")


class Dataset(Graph):
    def __init__(self, store="default", default_union=False, default_graph_base=None):
        super().__init__(store=store, base=default_graph_base)
        self.default_union = default_union
        self.default_graph = Graph(store=self.store, identifier=DATASET_DEFAULT_GRAPH_ID,
                                   namespace_manager=self.namespace_manager, base=default_graph_base)
        self._graphs = {DATASET_DEFAULT_GRAPH_ID: self.default_graph}

    def graph(self, identifier=None, base=None):
        source_graph = identifier if isinstance(identifier, Graph) and not isinstance(identifier, Dataset) else None
        identifier = BNode().skolemize() if identifier is None else identifier
        identifier = getattr(identifier, "identifier", identifier)
        if isinstance(identifier, str) and not isinstance(identifier, (URIRef, BNode)):
            identifier = URIRef(identifier)
        if not isinstance(identifier, (URIRef, BNode)):
            raise TypeError("graph identifier must be a URIRef or BNode")
        register = getattr(self.store, '_register_context', None)
        if identifier == self.default_graph.identifier:
            if register is not None:
                register(identifier)
            return self.default_graph
        graph = self._graphs.get(identifier)
        if graph is None:
            graph = Graph(store=self.store, identifier=identifier, namespace_manager=self.namespace_manager, base=base)
            self._graphs[identifier] = graph
        else:
            graph.base = base
        if register is not None:
            register(identifier)
        if source_graph is not None:
            for triple in source_graph:
                graph.add(triple)
        return graph

    def get_graph(self, identifier):
        """Return an existing graph; raise IndexError when it is absent."""
        if identifier in self._graphs:
            return self._graphs[identifier]
        for context in self.store.contexts():
            if context == identifier:
                return self.graph(identifier)
        raise IndexError("list index out of range")

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
        triple = triple_or_quad
        if len(triple) == 4:
            subject, predicate, obj, graph = triple
            self._assert_triple((subject, predicate, obj))
            if graph is None:
                self.store.add((subject, predicate, obj), None)
            else:
                self.graph(getattr(graph, "identifier", graph)).add((subject, predicate, obj))
        else:
            self.default_graph.add(triple)
        return self

    def addN(self, quads):
        for subject, predicate, obj, graph in quads:
            self.add((subject, predicate, obj, graph))
        return self

    def triples(self, triple_or_quad, context=None):
        if len(triple_or_quad) == 4:
            *pattern, selected = triple_or_quad
        else:
            pattern = triple_or_quad
            selected = None
        selected = context or selected
        selected = getattr(selected, 'identifier', selected)
        if self.default_union:
            if selected == self.default_graph.identifier:
                selected = None
        elif selected is None:
            selected = self.default_graph.identifier
        for triple, _ in self.store.triples(tuple(pattern), selected):
            yield triple

    def __len__(self):
        return self.store.__len__(None)

    def triples_choices(self, triple, context=None):
        if context is None:
            selected = None if self.default_union else self.default_graph.identifier
        elif isinstance(context, Graph):
            selected = context.identifier
        else:
            if context and not isinstance(context, (URIRef, BNode)):
                # RDFLib coerces through URIRef, whose URI validation requires
                # an iterable value. Preserve that error before querying.
                ' ' in context
            selected = self.get_context(context or None).identifier
        yield from self._choices(triple, lambda pattern: (row for row, _ in self.store.triples(pattern, selected)))

    def __iter__(self):
        return self.quads()

    def _triples_in_context(self, pattern):
        for triple, _ in self.store.triples(pattern, self.default_graph.identifier):
            yield triple

    def serialize(self, destination=None, format="trig", base=None, encoding=None, **args):
        return super().serialize(destination=destination, format=format, base=base, encoding=encoding, **args)

    def quads(self, quad=None):
        pattern = (None, None, None, None) if quad is None else quad
        if len(pattern) == 3:
            pattern = (*pattern, None)
        if len(pattern) != 4:
            raise ValueError("quad pattern must contain four elements")
        subject, predicate, obj, graph = pattern
        contexts = (
            list(dict.fromkeys(self.store.contexts()))
            if graph is None
            else [getattr(graph, "identifier", graph)]
        )
        for context in contexts:
            actual_graph = self.graph(context)
            for triple in actual_graph._triples_in_context((subject, predicate, obj)):
                yield (*triple, context)

    def graphs(self, triple=None):
        seen = set()
        for context in self.store.contexts(triple):
            if context in seen:
                continue
            seen.add(context)
            yield self.graph(context)
        if self.default_graph.identifier not in seen:
            yield self.default_graph

    def remove(self, triple_or_quad):
        pattern = triple_or_quad
        if len(pattern) == 4:
            subject, predicate, obj, graph = pattern
            contexts = (
                list(dict.fromkeys(self.store.contexts()))
                if graph is None
                else [getattr(graph, "identifier", graph)]
            )
            for context in contexts:
                self.graph(context).remove((subject, predicate, obj))
            return self
        self.store.remove(pattern, None)
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

    def contexts(self, triple=None):
        warnings.warn("contexts is deprecated; use graphs", DeprecationWarning, stacklevel=2)
        yield from self.graphs(triple)


class ConjunctiveGraph(Graph):
    # Dataset conveniences retained as RDFCore extensions; the class itself
    # follows RDFLib's Graph hierarchy and union-query contract.
    graph = Dataset.graph
    graphs = Dataset.graphs
    context_id = Dataset.context_id
    remove_context = Dataset.remove_context
    remove_graph = Dataset.remove_graph
    add_graph = Dataset.add_graph
    add = Dataset.add
    addN = Dataset.addN
    remove = Dataset.remove
    triples_choices = Dataset.triples_choices
    _triples_in_context = Dataset._triples_in_context

    def contexts(self, triple=None):
        for context in self.store.contexts(triple):
            yield context if isinstance(context, Graph) else self.get_context(context)

    def get_graph(self, identifier):
        return [graph for graph in self.contexts() if graph.identifier == identifier][0]

    def get_context(self, identifier, quoted=False, base=None):
        return Graph(store=self.store, identifier=identifier or None,
                     namespace_manager=self.namespace_manager, base=base)

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
        identifier = getattr(selected, 'identifier', selected)
        for triple, _ in self.store.triples((subject, predicate, obj), identifier):
            yield triple

    def quads(self, triple_or_quad=None):
        subject, predicate, obj, context = self._spoc(triple_or_quad)
        identifier = getattr(context, 'identifier', context)
        from .store import Memory, SQLiteStore
        for triple, contexts in self.store.triples((subject, predicate, obj), identifier):
            if type(self.store) in (Memory, SQLiteStore):
                contexts = (self.get_context(key) for key in self.store.contexts(triple))
            for selected in contexts:
                yield (*triple, selected)

    def __contains__(self, triple_or_quad):
        subject, predicate, obj, context = self._spoc(triple_or_quad)
        return next(self.triples((subject, predicate, obj), context=context), None) is not None

    def __len__(self):
        return self.store.__len__()

    def __iter__(self):
        return self.triples((None, None, None))

    def __init__(self, store="default", identifier=None, default_graph_base=None):
        Graph.__init__(self, store=store, identifier=identifier or None)
        if type(self) is ConjunctiveGraph:
            warnings.warn("ConjunctiveGraph is deprecated, use Dataset instead.",
                          DeprecationWarning, stacklevel=2)
        assert self.store.context_aware, "ConjunctiveGraph must be backed by a context aware store."
        self.context_aware = True
        self.default_union = True
        self.default_graph = Graph(store=self.store, identifier=identifier or BNode(),
                                   base=default_graph_base)
        self._graphs = {self.default_graph.identifier: self.default_graph}

    @property
    def default_context(self):
        return self.default_graph

    @default_context.setter
    def default_context(self, value):
        self.default_graph = value

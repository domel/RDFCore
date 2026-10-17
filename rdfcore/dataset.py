"""RDF dataset and legacy conjunctive graph APIs."""

from __future__ import annotations

import warnings

from .graph import Graph
from .term import BNode, URIRef

DATASET_DEFAULT_GRAPH_ID = URIRef("urn:x-rdflib:default")


class Dataset(Graph):
    def __init__(self, store="default", default_union=False, default_graph_base=None):
        super().__init__(store=store, identifier=DATASET_DEFAULT_GRAPH_ID, base=default_graph_base)
        self.default_union = default_union
        self.default_graph = Graph(store=self.store, identifier=DATASET_DEFAULT_GRAPH_ID,
                                   namespace_manager=self.namespace_manager, base=default_graph_base)
        self._graphs = {DATASET_DEFAULT_GRAPH_ID: self}

    def graph(self, identifier=None, base=None):
        source_graph = identifier if isinstance(identifier, Graph) and not isinstance(identifier, Dataset) else None
        identifier = BNode().skolemize() if identifier is None else identifier
        identifier = getattr(identifier, "identifier", identifier)
        if isinstance(identifier, str) and not isinstance(identifier, (URIRef, BNode)):
            identifier = URIRef(identifier)
        if not isinstance(identifier, (URIRef, BNode)):
            raise TypeError("graph identifier must be a URIRef or BNode")
        if identifier == DATASET_DEFAULT_GRAPH_ID:
            return self.default_graph
        graph = self._graphs.get(identifier)
        if graph is None:
            graph = Graph(store=self.store, identifier=identifier, namespace_manager=self.namespace_manager, base=base)
            self._graphs[identifier] = graph
        else:
            graph.base = base
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
            self.graph(getattr(graph, "identifier", graph)).add((subject, predicate, obj))
        else:
            super().add(triple)
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
            if selected == DATASET_DEFAULT_GRAPH_ID:
                selected = None
        elif selected is None:
            selected = DATASET_DEFAULT_GRAPH_ID
        for triple, _ in self.store.triples(tuple(pattern), selected):
            yield triple

    def __len__(self):
        return self.store.__len__(None)

    def __iter__(self):
        return self.quads()

    def _triples_in_context(self, pattern):
        for triple, _ in self.store.triples(pattern, DATASET_DEFAULT_GRAPH_ID):
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
        if identifier == DATASET_DEFAULT_GRAPH_ID:
            self.default_graph.remove((None, None, None))
        else:
            self.store.remove_context(identifier)
            self._graphs.pop(identifier, None)
        return self

    @property
    def default_context(self):
        warnings.warn("default_context is deprecated; use default_graph", DeprecationWarning, stacklevel=2)
        return self.default_graph

    def contexts(self, triple=None):
        warnings.warn("contexts is deprecated; use graphs", DeprecationWarning, stacklevel=2)
        yield from self.graphs(triple)


class ConjunctiveGraph(Dataset):
    def __iter__(self):
        return self.triples((None, None, None))

    def __init__(self, store="default", identifier=None):
        warnings.warn("ConjunctiveGraph is deprecated; use Dataset", DeprecationWarning, stacklevel=2)
        super().__init__(store=store, default_union=True)
        if identifier is not None:
            self.conjunctive_identifier = identifier

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
        self.default_graph = self
        self._graphs = {DATASET_DEFAULT_GRAPH_ID: self}

    def graph(self, identifier=None):
        identifier = DATASET_DEFAULT_GRAPH_ID if identifier is None else identifier
        if not isinstance(identifier, (URIRef, BNode)):
            raise TypeError("graph identifier must be a URIRef or BNode")
        if identifier == DATASET_DEFAULT_GRAPH_ID:
            return self
        graph = self._graphs.get(identifier)
        if graph is None:
            graph = Graph(store=self.store, identifier=identifier, namespace_manager=self.namespace_manager)
            self._graphs[identifier] = graph
        return graph

    def add(self, triple):
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

    def triples(self, pattern):
        if self.default_union:
            for triple, _ in self.store.triples(pattern, None):
                yield triple
        else:
            yield from self._triples_in_context(pattern)

    def _triples_in_context(self, pattern):
        for triple, _ in self.store.triples(pattern, DATASET_DEFAULT_GRAPH_ID):
            yield triple

    def quads(self, pattern=(None, None, None, None)):
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

    def remove(self, pattern):
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
        return super().remove(pattern)

    def remove_graph(self, graph):
        identifier = getattr(graph, "identifier", graph)
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
    def __init__(self, store="default", identifier=None):
        warnings.warn("ConjunctiveGraph is deprecated; use Dataset", DeprecationWarning, stacklevel=2)
        super().__init__(store=store, default_union=True)
        if identifier is not None:
            self.conjunctive_identifier = identifier
